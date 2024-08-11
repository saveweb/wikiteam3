import datetime

from wikiteam3.dumpgenerator.version import getVersion


def welcome():
    """Opening message"""

    welcome_string = f"# Welcome to DumpGenerator {getVersion()} by WikiTeam3 (GPL v3)"
    welcome_string += " " * (73 - len(welcome_string) - 1) + "#"
    copyright_string = f"# Copyright (C) 2011-{datetime.datetime.now(datetime.timezone.utc).year} WikiTeam developers"
    copyright_string += " " * (73 - len(copyright_string) - 1) + "#"

    return f"""\
#########################################################################
{welcome_string}
# More info at: <https://github.com/saveweb/wikiteam3>                  #
{copyright_string}
#########################################################################
"""


def bye(wikidump_dir = None):
    """Closing message"""
    print(
f"""
---> Done <---

If this is a public wiki, please, consider publishing this dump to the Internet Archive:

`wikiteam3uploader {wikidump_dir if wikidump_dir else ''}`

Good luck! Bye!
"""
)