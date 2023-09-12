""" Provide login functions """

from typing import Optional
import requests
import time

from wikiteam3.utils.login.api import bot_login, client_login, fetch_login_token
from wikiteam3.utils.login.index import index_login


def uniLogin(api: Optional[str] = '', index: Optional[str] = '' ,session: requests.Session = requests.Session(), username: str = '', password: str = ''):
    """ Try to login to a wiki using various methods.\n
    Return `session` if success, else return `None`.\n
    Try: `cilent login (api) => bot login (api) => index login (index)` """

    if (not api and not index) or (not username or not password):
        raise ValueError('uniLogin: api or index or username or password is empty')

    if api:
        print("Trying to log in to the wiki using clientLogin... (MW 1.27+)")
        _session = client_login(api=api, session=session, username=username, password=password)
        if _session:
            return _session
        time.sleep(5)

        print("Trying to log in to the wiki using botLogin... (MW 1.27+)")
        _session = bot_login(api=api, session=session, username=username, password=password)
        if _session:
            return _session
        time.sleep(5)

    if index:
        print("Trying to log in to the wiki using indexLogin... (generic)")
        _session = index_login(index=index, session=session, username=username, password=password)
        if _session:
            return _session

    return None
