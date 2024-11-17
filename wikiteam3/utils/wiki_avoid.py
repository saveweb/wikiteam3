import re
import sys
from urllib.parse import urlparse

import requests

from wikiteam3.dumpgenerator.config import Config, OtherConfig

def avoid_WikiMedia_projects(config: Config, other: OtherConfig):
    """Skip Wikimedia projects and redirect to the dumps website"""

    # notice about wikipedia dumps
    url = ""
    if config.api:
        url = url + config.api
    if config.index:
        url = url + config.index
    if re.findall(
        r"(?i)(wikipedia|wikisource|wiktionary|wikibooks|wikiversity|wikimedia|wikispecies|wikiquote|wikinews|wikidata|wikivoyage)\.org",
        url,
    ):
        print("PLEASE, DO NOT USE THIS SCRIPT TO DOWNLOAD WIKIMEDIA PROJECTS!")
        print("Download the dumps from http://dumps.wikimedia.org")
        if not other.force:
            print("Thanks!")
            sys.exit(2)

def avoid_robots_disallow(config: Config, other: OtherConfig):
    """Check if the robots.txt allows the download"""
    url = config.api or config.index
    exit_ = False
    try:
        # Don't use the session.get() method here, since we want to avoid the session's retry logic
        r = requests.get(
            urlparse(url).scheme + '://' + urlparse(url).netloc + '/robots.txt',
            cookies=other.session.cookies, headers=other.session.headers, verify=other.session.verify, proxies=other.session.proxies
        )
        if r.status_code == 200:
            if 'user-agent: wikiteam3\ndisallow: /' in r.text.lower():
                print('This wiki not allow wikiteam3 to archive.')
                exit_ = True
    except Exception as e:
        print('Error: cannot get robots.txt', e)

    if exit_:
        sys.exit(20)
