import datetime

from wikiteam3.dumpgenerator.version import getVersion


def welcome():
    message = ""
    """Opening message"""
    message += "#" * 73
    message += "\n"
    welcome_string = "# Welcome to DumpGenerator %s by WikiTeam3 (GPL v3)" % (
        getVersion()
    )
    welcome_string += " " * (73 - len(welcome_string) - 1) + "#"
    message += welcome_string
    message += "\n"
    message += (
        "# More info at: https://github.com/saveweb/wikiteam3                  #"
    )
    message += "\n"
    message += (
        "# Copyright (C) 2011-%d WikiTeam developers                           #\n"
        % (datetime.datetime.now().year)
    )
    message += "#" * 73

    return message


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