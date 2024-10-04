import argparse
from datetime import datetime
import json
import os
import random
import re
import shutil
from dataclasses import dataclass
import sys
import time
import traceback
from typing import Dict, List, Optional, Tuple, Union
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from internetarchive import get_item, Item
from file_read_backwards import FileReadBackwards

from wikiteam3.dumpgenerator.api.page_titles import checkTitleOk
from wikiteam3.dumpgenerator.config import Config, load_config
from wikiteam3.dumpgenerator.version import getVersion
from wikiteam3.uploader.socketLock import NoLock, SocketLockServer
from wikiteam3.utils import url2prefix_from_config, sha1sum
from wikiteam3.uploader.compresser import ZstdCompressor, SevenZipCompressor
from wikiteam3.utils.ia_checker import ia_s3_tasks_load_avg
from wikiteam3.utils.util import ALL_DUMPED_MARK, UPLOADED_MARK, XMLRIVISIONS_INCREMENTAL_DUMP_MARK, is_empty_dir, mark_as_done, is_markfile_exists

DEFAULT_COLLECTION = 'opensource'
TEST_COLLECTION = 'test_collection'
"""
items here are expected to be automatically removed after 30 days. 
(see <https://archive.org/details/test_collection?tab=about>)
"""
WIKITEAM_COLLECTION = 'wikiteam'
""" Only admins can add/move items to this collection. """

IDENTIFIER_PREFIX = "wiki-"

@dataclass
class IAKeys:
    access: str
    secret: str

@dataclass
class Args:
    keys_file: Path
    collection: str
    dry_run: bool
    update: bool
    wikidump_dir: Path

    bin_zstd: str
    zstd_level: int
    bin_7z: str
    parallel: bool

    rezstd: bool
    rezstd_endpoint: str

    def __post_init__(self):
        self.keys_file = Path(self.keys_file).expanduser().resolve()
        if not self.keys_file.exists():
            raise FileNotFoundError(f"Keys file {self.keys_file} does not exist")
        self.wikidump_dir = Path(self.wikidump_dir).expanduser().resolve()
        if not self.wikidump_dir.exists():
            raise FileNotFoundError(f"wikidump_dir {self.wikidump_dir} does not exist")


def read_ia_keys(path: Path) -> IAKeys:
    with open(path.expanduser().resolve()) as f:
        lines = f.readlines()

    access = lines[0].strip()
    secret = lines[1].strip()

    return IAKeys(access, secret)


def config2basename(config: Config) -> str:
    basename = "{}-{}".format(
        url2prefix_from_config(config=config),
        config.date,
    )
    return basename


def xmldump_is_complete(xml_path: Union[str, Path]) -> bool:
    lines_left = 100
    with FileReadBackwards(xml_path, encoding="utf-8") as frb:
        for l in frb:
            if l.strip() == "</mediawiki>":
                # xml dump is complete
                return True

            lines_left -= 1
            if lines_left <= 0:
                return False
    
    return False


def images_list_is_complete(images_txt_path: Union[str, Path]) -> bool:
    lines_left = 3
    with FileReadBackwards(images_txt_path, encoding="utf-8") as frb:
        for l in frb:
            if l.strip() == "--END--":
                # images list is complete
                return True

            lines_left -= 1
            if lines_left <= 0:
                return False
    
    return False

def get_xml_filename(config: Config) -> str:
    xml_filename = "{}-{}.xml".format(
        config2basename(config),
        "current" if config.curonly else "history",
    )
    return xml_filename


def prepare_xml_zst_file(wikidump_dir: Path, config: Config, *, parallel: bool,
                         zstd_compressor: ZstdCompressor, zstd_level: int
                         ) -> Path:
    """ Compress xml file to .zst file."""
    xml_filename = get_xml_filename(config)

    xml_file_path = wikidump_dir / xml_filename
    xml_zstd_file_path = wikidump_dir / f"{xml_filename}.zst"

    assert xml_file_path.exists() or xml_zstd_file_path.exists()

    if xml_file_path.exists():
        assert xmldump_is_complete(xml_file_path)
        with NoLock() if parallel else SocketLockServer():
            # ensure only one process is compressing, to avoid OOM
            r = zstd_compressor.compress_file(xml_file_path, level=zstd_level)
            assert r == xml_zstd_file_path.resolve()
            assert xml_zstd_file_path.exists()
            assert zstd_compressor.test_integrity(r)

            # rm source xml file
            # decompressing is so fast that we don't need to keep the xml file
            # os.remove(xml_file_path)

    assert xml_zstd_file_path.exists()

    return xml_zstd_file_path.resolve()


def prepare_images_7z_archive(wikidump_dir: Path, config: Config, parallel: bool, *,
                              images_source: str = "images",
                              sevenzip_compressor: SevenZipCompressor) -> Optional[Path]:
    """ Compress wikidump_dir/images_source dir to .7z file. 
    
    return:
        Path: to the .7z archive
        None: the dir is empty.
    """
    images_dir = wikidump_dir / images_source
    assert images_source in ["images", "images_mismatch"]
    assert images_dir.exists() and images_dir.is_dir()

    if is_empty_dir(images_dir):
        return None

    images_7z_archive_path = wikidump_dir / f"{config2basename(config)}-{images_source}.7z"
    if not images_7z_archive_path.exists() or not images_7z_archive_path.is_file():
        with NoLock() if parallel else SocketLockServer():
            r = sevenzip_compressor.compress_dir(images_dir)
            shutil.move(r, images_7z_archive_path)

    assert sevenzip_compressor.test_integrity(images_7z_archive_path)

    assert images_7z_archive_path.exists() and images_7z_archive_path.is_file()
    return images_7z_archive_path.resolve()


def prepare_files_to_upload(wikidump_dir: Path, config: Config, item: Item, *, parallel: bool,
                            zstd_compressor: ZstdCompressor, zstd_level: int,
                            sevenzip_compressor: SevenZipCompressor
                            ) -> Dict[str, str]:
    """ return: filedict ("remote filename": "local filename") """
    filedict = {} # "remote filename": "local filename"

    # config.json
    config_json_path = wikidump_dir / "config.json"
    assert config_json_path.exists()
    filedict[f"{config2basename(config)}-dumpMeta/config.json"] = str(config_json_path)

    # errors.log optional
    if (wikidump_dir / "errors.log").exists():
        filedict[f"{config2basename(config)}-dumpMeta/errors.log"] = str(wikidump_dir / "errors.log")
    # SpecialVersion.html optional
    if (wikidump_dir / "SpecialVersion.html").exists():
        filedict[f"{config2basename(config)}-dumpMeta/SpecialVersion.html"] = str(wikidump_dir / "SpecialVersion.html")
    # siteinfo.json optional
    if (wikidump_dir / "siteinfo.json").exists():
        filedict[f"{config2basename(config)}-dumpMeta/siteinfo.json"] = str(wikidump_dir / "siteinfo.json")
    # index.html optional
    if (wikidump_dir / "index.html").exists():
        filedict[f"{config2basename(config)}-dumpMeta/index.html"] = str(wikidump_dir / "index.html")

    print("=== commpressing necessary files: ===")

    # .xml dump
    if config.xml:
        if not config.xmlrevisions:
            #  -titles.txt
            titles_txt_path = wikidump_dir / f"{config2basename(config)}-titles.txt"
            titles_txt_zstd_path = wikidump_dir / f"{config2basename(config)}-titles.txt.zst"
            assert titles_txt_path.exists()
            assert checkTitleOk(config)
            r = zstd_compressor.compress_file(titles_txt_path,level=zstd_level)
            assert r == titles_txt_zstd_path.resolve()
            assert zstd_compressor.test_integrity(r)
            filedict[f"{config2basename(config)}-dumpMeta/{titles_txt_zstd_path.name}"] = str(titles_txt_zstd_path)
        xml_zstd_path = prepare_xml_zst_file(wikidump_dir, config, parallel=parallel, zstd_compressor=zstd_compressor, zstd_level=zstd_level)
        filedict[f"{xml_zstd_path.name}"] = str(xml_zstd_path)

    # images
    if config.images:
        # images.txt
        images_txt_path = wikidump_dir / f"{config2basename(config)}-images.txt"
        images_txt_zstd_path = wikidump_dir / f"{config2basename(config)}-images.txt.zst"
        assert images_list_is_complete(images_txt_path)
        r = zstd_compressor.compress_file(images_txt_path, level=zstd_level)
        assert r == images_txt_zstd_path.resolve()
        assert zstd_compressor.test_integrity(r)
        filedict[f"{config2basename(config)}-dumpMeta/{images_txt_zstd_path.name}"] = str(images_txt_zstd_path)

        # images.7z and images_mismatch.7z
        for images_source in ["images", "images_mismatch"]:
            # <--- TODO: remove this block in v4.2.1
            if images_source == "images_mismatch" and not (wikidump_dir / images_source).exists():
                print(f"{images_source} dir not found, skip")
                continue
            # --->
            images_7z_archive_path = prepare_images_7z_archive(wikidump_dir, config, parallel, images_source=images_source, sevenzip_compressor=sevenzip_compressor)
            if images_7z_archive_path:
                filedict[f"{images_7z_archive_path.name}"] = str(images_7z_archive_path)
            else:
                print(f"{images_source} dir is empty, skip creating .7z archive")

    print("=== Files already uploaded: ===")
    c = 0
    for file_in_item in item.files:
        if file_in_item["name"] in filedict:
            c += 1
            if int(file_in_item["size"]) != os.path.getsize(filedict[file_in_item["name"]]):
                print(f'    "{file_in_item["name"]}" (size mismatch), will re-upload')
                continue

            filedict.pop(file_in_item["name"])
            print(f'    "{file_in_item["name"]}" (already uploaded)')
    print(f"Already uploaded {c} files. ({len(item.files)} files in remote item in total)")

    print("=== Files to upload: ===")
    for remote_dest, local_src in filedict.items():
        print(f'    "{remote_dest}" from "{local_src}"')
    print(f"{len(filedict)} files ready to upload...")

    return filedict

def prepare_item_metadata(wikidump_dir: Path, config: Config, arg: Args) -> Tuple[Dict, Optional[str]]:
    """ return: (IA item metadata dict, logo_url) """

    wiki_prefix: str = url2prefix_from_config(config=config, ascii_slugify=False) # e.g. wiki.example.org

    sitename: Optional[str] = None # or empty str
    rights_text: Optional[str] = None # or empty str
    rights_url: Optional[str] = None # or empty str
    lang: Optional[str] = None # or empty str
    base_url: Optional[str] = None # or empty str
    logo_url: Optional[str] = None # or empty str
    if (wikidump_dir / "siteinfo.json").exists():
        with open(wikidump_dir / "siteinfo.json", "r", encoding="utf-8") as f:
            siteinfo: Dict = json.load(f)

        general = siteinfo.get("query", {}).get("general", {})
        rightsinfo = siteinfo.get("query", {}).get("rightsinfo", {})


        sitename = general.get("sitename", None)
        assert isinstance(sitename, str) or sitename is None

        base_url = general.get("base", None)
        assert isinstance(base_url, str) or base_url is None
        if base_url:
            if base_url.startswith("//"):
                print(f"WARNING: base_url {base_url} starts with // (protocol-relative URLs), will convert to https://")
                # Convert protocol-relative URLs
                base_url = re.sub(r"^//", r"https://", base_url)

        logo_url = general.get("logo", None)

        lang = general.get("lang", None)
        assert isinstance(lang, str) or lang is None

        rights_text = rightsinfo.get("text", None)
        assert isinstance(rights_text, str) or rights_text is None

        rights_url = rightsinfo.get("url", None)
        if rights_url and "www.fandom.com" in rights_url and "/licensing" in rights_url:
            # Link the default license directly instead
            rights_url = "https://creativecommons.org/licenses/by-sa/3.0/"

        assert isinstance(rights_url, str) or rights_url is None

    if config.xml:
        xml_file_path = wikidump_dir / get_xml_filename(config)
        assert xml_file_path.exists()
        with open(xml_file_path, "rb") as f:
            xmlheader = f.read(1024 * 1024) # 1MiB
        # get sitename from xmlheader
        if not sitename and b"<sitename>" in xmlheader:
            sitename = xmlheader.split(b"<sitename>", 1)[1].split(b"</sitename>", 1)[0].decode("utf-8")
        if not base_url and b"<base>" in xmlheader:
            base_url = xmlheader.split(b"<base>", 1)[1].split(b"</base>", 1)[0].decode("utf-8")
    
    if not base_url:
        base_url = re.sub(r"(?im)/api\.php", r"", config.api or config.index)

    keywords = [
        "wiki",
        "wikiteam",
        "wikiteam3",
        "MediaWiki",
        wiki_prefix,
    ]
    if sitename:
        keywords.append(sitename)
    if not rights_url and not rights_text:
        keywords.append("unknowncopyright")

    licenseurl: Optional[str] = urllib.parse.urljoin(config.api or config.index, rights_url) if rights_url else None
    description =  f'<a href="{base_url}">{sitename or wiki_prefix}</a> dumped with <a href="https://github.com/saveweb/wikiteam3/" rel="nofollow">wikiteam3</a> tools.'

    metadata = {
        "mediatype": "web",
        "collection": arg.collection,
        "title": "Wiki - " + (sitename or wiki_prefix),
        "description": description, # without URL, to bypass IA's anti-spam.
        "language": lang,
        "last-updated-date": time.strftime("%Y-%m-%d", time.gmtime()),
        "subject": "; ".join(
            keywords
        ),  # Keywords should be separated by ; but it doesn't matter much; the alternative is to set one per field with subject[0], subject[1], ...
        "licenseurl": licenseurl or None,
        "rights": rights_text or None,
        "originalurl": config.api or config.index,
        "upload-state": "uploading",
        "scanner": f"wikiteam3 (v{getVersion()})",
    }
    print("=== Item metadata: ===")
    print(json.dumps(metadata, indent=4, sort_keys=True, ensure_ascii=False))
    print(f"logo_url: {logo_url}")

    return metadata, logo_url

def upload(arg: Args):
    zstd_compressor = ZstdCompressor(bin_zstd=arg.bin_zstd, rezstd=arg.rezstd, rezstd_endpoint=arg.rezstd_endpoint)
    sevenzip_compressor = SevenZipCompressor(bin_7z=arg.bin_7z)
    ia_keys = read_ia_keys(arg.keys_file)
    wikidump_dir = arg.wikidump_dir
    wikidump_dir.name # {prefix}-{wikidump_dumpdate}-wikidump (e.g. wiki.example.org-20230730-wikidump)
    assert wikidump_dir.name.endswith("-wikidump"), f"Expected wikidump_dir to end with -wikidump, got {wikidump_dir.name}"

    print(f"=== Loading config from {wikidump_dir} ===")

    # load config
    init_config = Config()
    init_config.path = str(wikidump_dir)
    config = load_config(config_filename="config.json", config=init_config)

    config.path = str(wikidump_dir) # override path

    print(config)

    assert wikidump_dir == Path(config.path).resolve()

    assert is_markfile_exists(config, ALL_DUMPED_MARK), "Imcomplete dump"
    assert not is_markfile_exists(config, XMLRIVISIONS_INCREMENTAL_DUMP_MARK), "xmlrevisions incremental dump is not supported yet"
    if is_markfile_exists(config, UPLOADED_MARK):
        print(f"Already uploaded to IA ({UPLOADED_MARK} exists), bye!")
        return

    wikidump_dumpdate = wikidump_dir.name.split("-")[-2]
    assert config.date == wikidump_dumpdate
    if (not wikidump_dumpdate.isdigit()) or (not 20230730 < int(wikidump_dumpdate) < 9999_99_99):
        raise ValueError(f"Expected wikidump_dumpdate to be an 8-digit number, got {wikidump_dumpdate}")
    try:
        datetime.strptime(wikidump_dumpdate, "%Y%m%d")
    except ValueError as e:
        raise ValueError(f"Expected wikidump_dumpdate to be a valid date, got {wikidump_dumpdate}") from e

    # NOTE: Punycoded domain may contain multiple `-`
    # e.g. `xn--6qq79v.xn--rhqv96g-20230730-wikidump` (你好.世界_美丽-20230730-wikidump)
    _identifier = IDENTIFIER_PREFIX + url2prefix_from_config(config=config) + "-" + config.date
    identifier = IDENTIFIER_PREFIX + wikidump_dir.name.rstrip("-wikidump")
    assert identifier == _identifier

    item = get_item(identifier)

    print("=== Preparing files to upload ===")
    filedict = prepare_files_to_upload(
        wikidump_dir, config, item, parallel=arg.parallel, 
        zstd_compressor=zstd_compressor, zstd_level=arg.zstd_level,
        sevenzip_compressor=sevenzip_compressor
        )

    print("=== Preparing metadata ===")
    metadata, logo_url = prepare_item_metadata(wikidump_dir, config, arg)

    print("=== Checking IA S3 load average (optional) ===")

    try:
        avg_load = ia_s3_tasks_load_avg(session=item.session) # check IA load
        print(f"IA S3 load: {avg_load * 100:.4f}%")
        if avg_load > 0.99:
            print("WARNING: IA S3 is heavily overloaded,")
            print("To prevent IA S3 from being overloaded further, please try uploading later, exiting...")
            sys.exit(99)
        elif avg_load > 0.9:
            print("WARNING: IA S3 is overloaded, upload may fail") 
    except Exception as e:
        traceback.print_exc()
        print(f"Failed to get IA S3 load average: {e}")
        print("Don't worry, it's optional.")


    if arg.dry_run:
        print("=== Dry run, exiting ===")
        return

    print("=== Uploading ===")
    upload_main_resouces(item, filedict, metadata, ia_keys)

    item = get_item(identifier)
    if logo_url:
        print("=== Uploading logo (optional) ===")
        try:
            logo_url = urllib.parse.urljoin(config.api or config.index, logo_url)
            upload_logo(item, logo_url, ia_keys)
        except Exception as e:
            traceback.print_exc()
            print(f"Failed to upload logo: {e}")
            print("Don't worry, it's optional.")
    
    item = get_item(identifier)
    print("=== Updating upload-state ===")
    if item.metadata.get("upload-state") != "uploaded":
        r = item.modify_metadata({"upload-state": "uploaded"}, access_key=ia_keys.access, secret_key=ia_keys.secret)
        assert isinstance(r, requests.Response)
        print(r.text)
        r.raise_for_status()
    print("=== Uploading complete ===")
    print(f"identifier: {identifier}")
    print(f"URL: https://archive.org/details/{identifier}")
    mark_as_done(config, UPLOADED_MARK, msg=f"identifier: {identifier}")

def upload_logo(item: Item, logo_url: str, ia_keys: IAKeys):
    assert logo_url
    assert item.identifier

    parsed_url = urllib.parse.urlparse(logo_url)
    logo_suff = parsed_url.path.split(".")[-1].lower()
    if len(logo_suff) >= 7:
        logo_suff = "unknown"
    logo_name = item.identifier + "_logo." + logo_suff
    for file_ in item.files:
        if file_["name"] == logo_name:
            print(f"Logo {logo_name} already exists, skip")
            return
    logo_io = None
    for tries_left in range(4, 0, -1):
        try:
            logo_io = BytesIO(requests.get(logo_url, timeout=20).content)
            break
        except Exception:
            if tries_left == 1:
                raise
            print(f"Failed to download logo, retrying ({tries_left} tries left)")
            time.sleep(3)

    assert logo_io

    r_co = item.upload(
        {logo_name: logo_io},
        access_key=ia_keys.access,
        secret_key=ia_keys.secret,
        verbose=True,
    )
    for r_resp in r_co:
        assert isinstance(r_resp, requests.Response)
        print(r_resp.text)
        r_resp.raise_for_status()

def upload_main_resouces(item: Item, filedict: Dict[str, str], metadata: Dict, ia_keys: IAKeys):
    if not filedict:
        print("No files to upload, skip")
        return

    r_co = item.upload(
        files=filedict,
        metadata=metadata,
        access_key=ia_keys.access,
        secret_key=ia_keys.secret,
        verbose=True,
        queue_derive=False, # disable derive
    )
    for r_resp in r_co:
        assert isinstance(r_resp, requests.Response)
        print(r_resp.text)
        r_resp.raise_for_status()
    print(f"Uploading {len(filedict)} files: Done.\n")

    identifier = item.identifier
    assert identifier

    item = get_item(identifier) # refresh item
    tries = 400
    for tries_left in range(tries, 0, -1):
        if item.exists:
            break

        print(f"Waiting for item to be created ({tries_left} tries left)  ...", end='\r')
        if tries < 395:
            print(f"IA overloaded, still waiting for item to be created ({tries_left} tries left)  ...", end='\r')
        time.sleep(30)
        item = get_item(identifier)

    if not item.exists:
        raise TimeoutError(f"IA overloaded, item still not created after {400 * 30} seconds")

def main():
    parser = argparse.ArgumentParser(
        """ Upload wikidump to the Internet Archive."""
    )

    parser.add_argument("-kf", "--keys_file", default="~/.wikiteam3_ia_keys.txt", dest="keys_file",
                        help="Path to the IA S3 keys file. (first line: access key, second line: secret key)"
                             " [default: ~/.wikiteam3_ia_keys.txt]")
    parser.add_argument("-c", "--collection", default=DEFAULT_COLLECTION, choices=[DEFAULT_COLLECTION, TEST_COLLECTION, WIKITEAM_COLLECTION])
    parser.add_argument("--dry-run", action="store_true", help="Dry run, do not upload anything.")
    parser.add_argument("-u", "--update", action="store_true",
                        help="Update existing item. [!! not implemented yet !!]")
    parser.add_argument("--bin-zstd", default=ZstdCompressor.bin_zstd, dest="bin_zstd",
                        help=f"Path to zstd binary. [default: {ZstdCompressor.bin_zstd}]")
    parser.add_argument("--zstd-level", default=ZstdCompressor.DEFAULT_LEVEL, type=int, choices=range(17, 23),
                        help=f"Zstd compression level. [default: {ZstdCompressor.DEFAULT_LEVEL}] "
                        f"If you have a lot of RAM, recommend to use max level (22)."
                        )
    parser.add_argument("--rezstd", action="store_true", default=ZstdCompressor.rezstd, dest="rezstd",
                        help="[server-side recompression] Upload pre-compressed zstd files to rezstd server for recompression with "
                            "best settings (which may eat 10GB+ RAM), then download back. (This feature saves your lowend machine, lol)")
    parser.add_argument("--rezstd-endpoint", default=ZstdCompressor.rezstd_endpoint, metavar="URL", dest="rezstd_endpoint",
                        help=f"Rezstd server endpoint. [default: {ZstdCompressor.rezstd_endpoint}] "
                        f"(source code: https://github.com/yzqzss/rezstd)"
                        )
    parser.add_argument("--bin-7z", default=SevenZipCompressor.bin_7z, dest="bin_7z",
                        help=f"Path to 7z binary. [default: {SevenZipCompressor.bin_7z}] ")
    parser.add_argument("--parallel", action="store_true", help="Parallelize compression tasks")
    parser.add_argument("wikidump_dir")
    
    arg = Args(**vars(parser.parse_args()))
    print(arg)
    upload(arg)
    



if __name__ == "__main__":
    main()
