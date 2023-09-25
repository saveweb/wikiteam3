import contextlib
import os
import re
import subprocess
import sys
import traceback
from typing import Dict, Union

from file_read_backwards import FileReadBackwards

from wikiteam3.dumpgenerator.config import load_config, save_config
from wikiteam3.dumpgenerator.config import Config
from wikiteam3.dumpgenerator.cli import get_parameters, bye, welcome
from wikiteam3.dumpgenerator.dump.image.image import Image
from wikiteam3.dumpgenerator.dump.misc.index_php import save_IndexPHP
from wikiteam3.dumpgenerator.dump.misc.special_logs import save_SpecialLog
from wikiteam3.dumpgenerator.dump.misc.special_version import save_SpecialVersion
from wikiteam3.dumpgenerator.dump.misc.site_info import save_siteinfo
from wikiteam3.dumpgenerator.dump.xmldump.xml_dump import generate_XML_dump
from wikiteam3.dumpgenerator.dump.xmldump.xml_integrity import check_XML_integrity
from wikiteam3.dumpgenerator.log import log_error
from wikiteam3.utils import url2prefix_from_config, undo_HTML_entities, avoid_WikiMedia_projects
from wikiteam3.utils.ia_checker import any_recent_ia_item_exists
from wikiteam3.utils.util import ALL_DUMPED_MARK, mark_as_done, underscore

# From https://stackoverflow.com/a/57008707
class Tee(object):
    def __init__(self, filename):
        self.file = open(filename, 'w', encoding="utf-8")
        self.stdout = sys.stdout

    def __enter__(self):
        sys.stdout = self

    def __exit__(self, exc_type, exc_value, tb):
        sys.stdout = self.stdout
        if exc_type is not None:
            self.file.write(traceback.format_exc())
        self.file.close()

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
        self.stdout.flush()

class DumpGenerator:
    configfilename = "config.json"

    @staticmethod
    def __init__(params=None):
        """Main function"""
        config_filename = DumpGenerator.configfilename
        config, other = get_parameters(params=params)
        avoid_WikiMedia_projects(config=config, other=other)

        with (Tee(other["stdout_log_path"]) if other["stdout_log_path"] is not None else contextlib.nullcontext()):
            print(welcome())
            print("Analysing %s" % (config.api if config.api else config.index))

            # do not enter if resume is requested from begining
            while not other["resume"] and os.path.isdir(config.path):
                print('\nWarning!: "%s" path exists' % (config.path))
                reply = "y" if config.failfast else ""
                while reply.lower()[:1] not in ["y", "n"]:
                    reply = input(
                        'There is a dump in "%s", probably incomplete.\n'
                        'If you choose resume, to avoid conflicts, some parameters '
                        'you have chosen in the current session will be ignored\n'
                        'and the parameters available in "%s/%s" will be loaded.\n'
                        'Do you want to resume (y/n)? '
                        % (config.path, config.path, config_filename)
                    )
                    reply = reply.lower()[:1]
                if reply == "y":
                    if not os.path.isfile("{}/{}".format(config.path, config_filename)):
                        print("No config file found. I can't resume. Aborting.")
                        sys.exit(1)
                    print("You have selected: YES")
                    other["resume"] = True
                    break
                elif reply == "n":
                    print("You have selected: NO.\nbye.")
                    # other["resume"] = False
                    sys.exit(0)

            if other["resume"]:
                print("Loading config file...")
                config = load_config(config=config, config_filename=config_filename)
            else:
                if not other['force'] and any_recent_ia_item_exists(config, days=365):
                    print("A dump of this wiki was uploaded to IA in the last 365 days. Aborting.")
                    sys.exit(88)

                os.mkdir(config.path)
                save_config(config=config, config_filename=config_filename)

            if other["resume"]:
                DumpGenerator.resumePreviousDump(config=config, other=other)
            else:
                DumpGenerator.createNewDump(config=config, other=other)

            if config.index:
                save_IndexPHP(config=config, session=other["session"])
                save_SpecialVersion(config=config, session=other["session"])
            if config.api:
                save_siteinfo(config=config, session=other["session"])

            mark_as_done(config=config, mark=ALL_DUMPED_MARK)
            bye(config.path)
            if other["upload"]:
                print('Calling uploader... (--upload)')
                retcode = subprocess.call([sys.executable, '-m', 'wikiteam3.uploader', config.path] + other["uploader_args"],
                    shell=False)
                if retcode:
                    print(f'--upload: Failed: {retcode}')
                    sys.exit(retcode)
                
                print('--upload: Done')

    @staticmethod
    def createNewDump(config: Config, other: Dict):
        # we do lazy title dumping here :)
        images = []
        print("Trying generating a new dump into a new directory...")
        if config.xml:
            generate_XML_dump(config=config, session=other["session"])
            check_XML_integrity(config=config, session=other["session"])
        if config.images:
            images += Image.get_image_names(config=config, session=other["session"])
            Image.save_image_names(config=config, images=images)
            Image.generate_image_dump(
                config=config, other=other, images=images, session=other["session"]
            )
        if config.logs:
            pass # TODO
            # save_SpecialLog(config=config, session=other["session"])

    @staticmethod
    def resumePreviousDump(config: Config, other: Dict):
        images = []
        print("Resuming previous dump process...")
        if config.xml:

            # checking xml dump
            xml_is_complete = False
            last_xml_title = None
            last_xml_revid = None
            try:
                with FileReadBackwards(
                    "%s/%s-%s-%s.xml"
                    % (
                        config.path,
                        url2prefix_from_config(config=config),
                        config.date,
                        "current" if config.curonly else "history",
                    ),
                    encoding="utf-8",
                ) as frb:
                    for l in frb:
                        if l.strip() == "</mediawiki>":
                            # xml dump is complete
                            xml_is_complete = True
                            break

                        xmlrevid = re.search(r"    <id>([^<]+)</id>", l)
                        if xmlrevid:
                            last_xml_revid = int(xmlrevid.group(1))
                        xmltitle = re.search(r"<title>([^<]+)</title>", l)
                        if xmltitle:
                            last_xml_title = undo_HTML_entities(text=xmltitle.group(1))
                            break

            except Exception:
                pass  # probably file does not exists

            if xml_is_complete:
                print("XML dump was completed in the previous session")
            elif last_xml_title:
                # resuming...
                print('Resuming XML dump from "%s" (revision id %s)' % (last_xml_title, last_xml_revid))
                generate_XML_dump(
                    config=config,
                    session=other["session"],
                    resume=True,
                )
            else:
                # corrupt? only has XML header?
                print("XML is corrupt? Regenerating...")
                generate_XML_dump(config=config, session=other["session"])

        if config.images:
            # load images list
            lastimage = ""
            imagesFilePath = "%s/%s-%s-images.txt" % (config.path, url2prefix_from_config(config=config), config.date)
            if os.path.exists(imagesFilePath):
                f = open(imagesFilePath)
                lines = f.read().splitlines()
                for l in lines:
                    if re.search(r"\t", l):
                        images.append(l.split("\t"))
                if len(lines) == 0: # empty file
                    lastimage = "--EMPTY--"
                if lastimage == "":
                    lastimage = lines[-1].strip()
                if lastimage == "":
                    lastimage = lines[-2].strip()
                f.close()

            if len(images)>0 and len(images[0]) < 5:
                print(
                    "Warning: Detected old images list (images.txt) format.\n"+
                    "You can delete 'images.txt' manually and restart the script."
                )
                sys.exit(9)
            if lastimage == "--END--":
                print("Image list was completed in the previous session")
            else:
                print("Image list is incomplete. Reloading...")
                # do not resume, reload, to avoid inconsistences, deleted images or
                # so
                images = Image.get_image_names(config=config, session=other["session"])
                Image.save_image_names(config=config, images=images)
            # checking images directory
            files = set()
            du_dir: int = 0 # du -s {config.path}/images
            if os.path.exists(f"{config.path}/images"):
                c_loaded = 0
                for file in os.scandir(f"{config.path}/images"):
                    if not file.is_file():
                        print(f"Warning: {file.name} is not a file")
                        continue
                    if underscore(file.name) != file.name: # " " in filename
                        os.rename(f"{config.path}/images/{file.name}",
                                    f"{config.path}/images/{underscore(file.name)}")
                        print(f"Renamed {file.name} to {underscore(file.name)}")
                    files.add(underscore(file.name))
                    du_dir += file.stat().st_size
                    
                    c_loaded += 1
                    if c_loaded % 12000 == 0:
                        print(f"[progress] {c_loaded} files loaded...", end="\r")
                print(f"{c_loaded} files in $wikidump/images/ dir, du -s: {du_dir} bytes ({du_dir/1024/1024/1024:.2f} GiB)")

            def int_or_zero(size: Union[int, str]) -> int:
                return int(size) if (
                            size
                            and (
                                (isinstance(size, str) and size.isdigit())
                                or
                                (isinstance(size, int))
                            )
                        ) else 0


            c_images_size = 0
            c_images_downloaded = 0
            c_images_downloaded_size = 0
            c_checked = 0

            for filename, url, uploader, size, sha1, timestamp in images:
                if other["filenamelimit"] < len(filename.encode('utf-8')):
                    log_error(
                        config=config, to_stdout=True,
                        text=f"Filename too long(>240 bytes), skipping: {filename}",
                    )
                    continue
                if filename in files:
                    c_images_downloaded += 1
                    c_images_downloaded_size += int_or_zero(size)
                c_checked += 1
                c_images_size += int_or_zero(size)
                if c_checked % 100000 == 0:
                    print(f"checked {c_checked}/{len(images)} records", end="\r")
            print(f"{len(images)} records in images.txt, {c_images_downloaded} files were saved in the previous session")
            print(f"Estimated size of all images (images.txt): {c_images_size} bytes ({c_images_size/1024/1024/1024:.2f} GiB)")
            if c_images_downloaded < len(images):
                complete = False
                print("WARNING: Some images were not saved in the previous session")
            else:
                complete = True
            if complete:
                # image dump is complete
                print("Image dump was completed in the previous session")
            else:
                # we resume from previous image, which may be corrupted 
                # by the previous session ctrl-c or abort
                Image.generate_image_dump(
                    config=config,
                    other=other,
                    images=images,
                    session=other["session"],
                )

        if config.logs:
            # fix
            pass
