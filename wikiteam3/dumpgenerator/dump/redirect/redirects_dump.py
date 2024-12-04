

import json
import os
import requests
from wikiteam3.dumpgenerator.config import Config
from wikiteam3.dumpgenerator.dump.redirect.allredirects import get_redirects_by_allredirects
from wikiteam3.utils.identifier import url2prefix_from_config


def generate_redirects_dump(config: Config, resume=False, *, session: requests.Session):
    tmp_filename = "{}-{}-redirects.tmp".format(
        url2prefix_from_config(config=config), config.date
    )
    redirects_filename = "{}-{}-redirects.jsonl".format(
        url2prefix_from_config(config=config), config.date
    )

    if resume:
        if os.path.exists("{}/{}".format(config.path, redirects_filename)):
            print("redirects dump was completed in the previous session")
            return

        print("Resuming is not supported yet, regenerating the redirects dump")


    tmp_file = open(
        "{}/{}".format(config.path, tmp_filename), "w", encoding="utf-8"
    )
    for redirect in get_redirects_by_allredirects(config, session):
        print("    ", redirect)
        tmp_file.write(
            json.dumps(redirect, ensure_ascii=False, separators=(",", ":"))
            +"\n"
        )
    tmp_file.close()


    os.rename(
        "{}/{}".format(config.path, tmp_filename),
        "{}/{}".format(config.path, redirects_filename),
    )