import argparse
from datetime import datetime
import getopt
import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
import time
from typing import List
import urllib.parse
from io import BytesIO
from pathlib import Path

from wikiteam3.dumpgenerator.config import Config
from wikiteam3.utils import get_UserAgent, url2prefix_from_config
import requests
from internetarchive import get_item

from wikiteam3.utils.util import sha1sum

DEFAULT_COLLECTION = 'opensource'
TEST_COLLECTION = 'test_collection'
"""
items here are expected to be automatically removed after 30 days. 
(see <https://archive.org/details/test_collection?tab=about>)
"""
WIKITEAM_COLLECTION = 'wikiteam'
""" Only admins can add/move items to this collection. """


@dataclass
class IAKeys:
    access: str
    secret: str

@dataclass
class Args:
    keys_file: Path
    path7z: Path
    collection: str
    update: bool
    wikidump_dir: Path

    def __post_init__(self):
        self.keys_file = Path(self.keys_file).expanduser().resolve()
        self.path7z = Path(self.path7z).expanduser().resolve()
        self.wikidump_dir = Path(self.wikidump_dir).expanduser().resolve()
        if not self.keys_file.exists():
            raise FileNotFoundError(f"Keys file {self.keys_file} does not exist")


def read_ia_keys(path: Path) -> IAKeys:
    with open(path.expanduser().resolve()) as f:
        lines = f.readlines()

    access = lines[0].strip()
    secret = lines[1].strip()

    return IAKeys(access, secret)


def upload(arg: Args):
    ia_keys = read_ia_keys(arg.keys_file)
    wikidump_dir = arg.wikidump_dir
    wikidump_dir.name # {prefix}-20230730-wikidump

    assert wikidump_dir.name.endswith("-wikidump"), f"Expected wikidump_dir to end with -wikidump, got {wikidump_dir.name}"

    wikidump_dumpdate = wikidump_dir.name.split("-")[-2]
    assert wikidump_dumpdate.isdigit() == 8
    assert int(wikidump_dumpdate) > 20230730
    assert datetime.strptime(wikidump_dumpdate, "%Y%m%d")

    # NOTE: Punycoded domain may contain multiple `-`
    # e.g. `xn--6qq79v.xn--rhqv96g-20230730-wikidump` (你好.世界_美丽-20230730-wikidump)
    identifier = "wiki-" + wikidump_dir.name.rstrip("-wikidump")
    
    


    try:
        prefix = url2prefix_from_config(Config(api=wiki))
    except KeyError:
        raise

    wikiname = prefix.split("-")[0]
    dumps: List[Path] = []
    for f in wikidump_dir.iterdir():
        if f.name.startswith("%s-" % (wikiname)) and (f.name.endswith("-wikidump.7z") or f.name.endswith("-history.xml.7z")):
            print("%s found" % f)
            dumps.append(f)
            # Re-introduce the break here if you only need to upload one file
            # and the I/O is too slow
            # break

    c = 0
    identifier = "wiki-" + wikiname
    item = get_item(identifier)
    first_item_exists = item.exists
    for dump in dumps:
        wikidate = dump.name.split("-")[1]
        assert wikidate.isdigit()
        assert len(wikidate) == 8

        if first_item_exists:
            identifier = "wiki-" + wikiname  + "-" + wikidate
            item = get_item(identifier)
        if dump.name in uploadeddumps:
            if arg.prune_directories:
                rmpath = wikidump_dir / f"{wikiname}-{wikidate}-wikidump"
                if rmpath.exists():
                    shutil.rmtree(rmpath)
                    print(f"DELETED {rmpath.name}/")

            if arg.prune_wikidump and dump.name.endswith("wikidump.7z"):
                # Simplistic quick&dirty check for the presence of this file in the item
                print("Checking content in previously uploaded files")
                dumphash = sha1sum(dump)

                if dumphash in map(lambda x: x["md5"], item.files):
                    dump.unlink()
                    print("DELETED " + str(dump))
                    print("%s was uploaded before, skipping..." % (dump.name))
                    continue
                else:
                    print("ERROR: The online item misses " + dump.name)
                    # We'll exit this if and go upload the dump
            else:
                print("%s was uploaded before, skipping..." % (dump.name))
                continue
        else:
            print("%s was not uploaded before" % dump.name)

        time.sleep(0.1)
        wikidate_text = wikidate[0:4] + "-" + wikidate[4:6] + "-" + wikidate[6:8]
        print(wiki, wikiname, wikidate, dump)

        # Does the item exist already?
        ismissingitem = not item.exists

        # Logo path
        logourl: str = ""

        if ismissingitem or arg.update:
            # get metadata from api.php
            # first sitename and base url
            params = {"action": "query", "meta": "siteinfo", "format": "xml"}
            xml = ""
            try:
                r = requests.get(url=wiki, params=params, headers=headers)
                if r.status_code < 400:
                    xml = r.text
            except requests.exceptions.ConnectionError as e:
                print("ERROR: could not get siteinfo for %s" % wiki)

            sitename = ""
            baseurl = ""
            lang = ""
            try:
                sitename = re.findall(r"sitename=\"([^\"]+)\"", xml)[0]
            except:
                print("ERROR: could not get sitename for %s" % wiki)
            try:
                baseurl = re.findall(r"base=\"([^\"]+)\"", xml)[0]
            except:
                print("ERROR: could not get baseurl for %s" % wiki)
            try:
                lang = re.findall(r"lang=\"([^\"]+)\"", xml)[0]
            except:
                print("ERROR: could not get lang for %s" % wiki)

            if not sitename:
                sitename = wikiname
            if not baseurl:
                baseurl = re.sub(r"(?im)/api\.php", r"", wiki)
            # Convert protocol-relative URLs
            baseurl = re.sub("^//", "https://", baseurl)

            # now copyright info from API
            params = {
                "action": "query",
                "meta": "siteinfo",
                "siprop": "general|rightsinfo",
                "format": "xml",
            }
            xml = ""
            try:
                r = requests.get(url=wiki, params=params, headers=headers)
                if r.status_code < 400:
                    xml = r.text
            except requests.exceptions.ConnectionError as e:
                pass

            rightsinfourl = ""
            rightsinfotext = ""
            try:
                rightsinfourl = re.findall(r"rightsinfo url=\"([^\"]+)\"", xml)[0]
                rightsinfotext = re.findall(r"text=\"([^\"]+)\"", xml)[0]
            except:
                pass

            raw = ""
            try:
                r = requests.get(url=baseurl, headers=headers)
                if r.status_code < 400:
                    raw = r.text
            except requests.exceptions.ConnectionError as e:
                pass

            # or copyright info from #footer in mainpage
            if baseurl and not rightsinfourl and not rightsinfotext:
                print("INFO: Getting license from the HTML")
                rightsinfotext = ""
                rightsinfourl = ""
                try:
                    rightsinfourl = re.findall(
                        r"<link rel=\"copyright\" href=\"([^\"]+)\" />", raw
                    )[0]
                except:
                    pass
                try:
                    rightsinfotext = re.findall(
                        r"<li id=\"copyright\">([^\n\r]*?)</li>", raw
                    )[0]
                except:
                    pass
                if rightsinfotext and not rightsinfourl:
                    rightsinfourl = baseurl + "#footer"
            try:
                _logourl_list = re.findall(
                    r'p-logo["\'][^>]*>\s*<a [^>]*background-image:\s*(?:url\()?([^;)"]+)',
                    raw,
                )
                if _logourl_list:
                    logourl = _logourl_list[0]
                else:
                    logourl = re.findall(
                        r'"wordmark-image">[^<]*<a[^>]*>[^<]*<img src="([^"]+)"',
                        raw,
                    )[0]
                if "http" not in logourl:
                    # Probably a relative path, construct the absolute path
                    logourl = urllib.parse.urljoin(wiki, logourl)
            except:
                pass

            # retrieve some info from the wiki
            wikititle = "Wiki - %s" % (sitename)  # Wiki - ECGpedia
            wikidesc = (
                '<a href="%s">%s</a> dumped with <a href="https://github.com/mediawiki-client-tools/mediawiki-scraper/" rel="nofollow">MediaWiki-Scraper</a> (aka WikiTeam3) tools.'
                % (baseurl, sitename)
            )  # "<a href=\"http://en.ecgpedia.org/\" rel=\"nofollow\">ECGpedia,</a>: a free electrocardiography (ECG) tutorial and textbook to which anyone can contribute, designed for medical professionals such as cardiac care nurses and physicians. Dumped with <a href=\"https://github.com/WikiTeam/wikiteam\" rel=\"nofollow\">WikiTeam</a> tools."
            wikikeys = [
                "wiki",
                "wikiteam",
                "wikiteam3",
                "mediawiki-scraper",
                "mediawikiScraper",
                "MediaWiki",
                sitename,
                wikiname,
            ]  # ecg; ECGpedia; wiki; wikiteam; MediaWiki

            if not rightsinfourl and not rightsinfotext:
                wikikeys.append("unknowncopyright")
            if "www.fandom.com" in rightsinfourl and "/licensing" in rightsinfourl:
                # Link the default license directly instead
                rightsinfourl = "https://creativecommons.org/licenses/by-sa/3.0/"
            wikilicenseurl = (
                rightsinfourl  # http://creativecommons.org/licenses/by-nc-sa/3.0/
            )
            wikirights = rightsinfotext  # e.g. http://en.ecgpedia.org/wiki/Frequently_Asked_Questions : hard to fetch automatically, could be the output of API's rightsinfo if it's not a usable licenseurl or "Unknown copyright status" if nothing is found.

            wikiurl = wiki  # we use api here http://en.ecgpedia.org/api.php
        else:
            # bool(ismissingitem or config.update) == False
            print("Item already exists.")
            lang = "foo"
            wikititle = "foo"
            wikidesc = "foo"
            wikikeys = "foo"
            wikilicenseurl = "foo"
            wikirights = "foo"
            wikiurl = "foo"

        # Item metadata
        md = {
            "mediatype": "web",
            "collection": arg.collection,
            "title": wikititle,
            "description": wikidesc,
            "language": lang,
            "last-updated-date": wikidate_text,
            "subject": "; ".join(
                wikikeys
            ),  # Keywords should be separated by ; but it doesn't matter much; the alternative is to set one per field with subject[0], subject[1], ...
            "licenseurl": wikilicenseurl
            and urllib.parse.urljoin(wiki, wikilicenseurl),
            "rights": wikirights,
            "originalurl": wikiurl,
        }

        # Upload files and update metadata
        try:
            item.upload(
                str(dump),
                metadata=md,
                access_key=ia_keys.access,
                secret_key=ia_keys.secret,
                verbose=True,
                queue_derive=False,
            )
            retry = 20
            while not item.exists and retry > 0:
                retry -= 1
                print('Waitting for item "%s" to be created... (%s)' % (identifier, retry))
                time.sleep(10)
                item = get_item(identifier)

            # Update metadata
            r = item.modify_metadata(md,
                                access_key=ia_keys["access"], secret_key=ia_keys["secret"])
            assert isinstance(r, requests.models.Response)
            if r.status_code != 200:
                print("Error when updating metadata")
                print(r.status_code)
                print(r.text)

            print(
                "You can find it in https://archive.org/details/%s"
                % (identifier)
            )
            uploadeddumps.append(dump.name)
        except Exception as e:
            print(wiki, dump, "Error when uploading?")
            print(e)
        try:
            if logourl:
                logo = BytesIO(requests.get(logourl, timeout=10).content)
                if ".png" in logourl:
                    logoextension = "png"
                elif logourl.split("."):
                    logoextension = logourl.split(".")[-1]
                else:
                    logoextension = "unknown"
                logoname = "wiki-" + wikiname + "_logo." + logoextension
                item.upload(
                    {logoname: logo},
                    access_key=ia_keys.access,
                    secret_key=ia_keys.secret,
                    verbose=True,
                )
        except requests.exceptions.ConnectionError as e:
            print(wiki, dump, "Error when uploading logo?")
            print(e)

        c += 1


def main():
    parser = argparse.ArgumentParser(
        """ Upload wikidump to the Internet Archive."""
    )

    parser.add_argument("-kf", "--keys_file", default="~/.mw_ia_keys.txt", dest="keys_file",
                        help="Path to the IA S3 keys file. (first line: access key, second line: secret key)"
                             " [default: ~/.mw_ia_keys.txt]")
    parser.add_argument("-p7z", "--path7z", default="7z",
                        help="Path to 7z binary. [default: 7z]")
    parser.add_argument("-u", "--update", action="store_true")
    parser.add_argument("-c", "--collection", default=DEFAULT_COLLECTION, choices=[DEFAULT_COLLECTION, TEST_COLLECTION, WIKITEAM_COLLECTION])
    parser.add_argument("wikidump_dir")
    
    arg = Args(**vars(parser.parse_args()))
    print(arg)
    upload(arg)
    



if __name__ == "__main__":
    main()
