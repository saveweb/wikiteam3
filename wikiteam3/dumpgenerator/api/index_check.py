import re
import time

import requests

class print_probability:
    """ Decorator for printing the return value of a function """

    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        ret = self.func(*args, **kwargs)
        print(f"index.php available probability: {ret*100:.0f}% ({ret})")
        return ret

@print_probability
def check_index(*, index: str, logged_in: bool, session: requests.Session) -> float:
    """ Checking index.php availability
    
    returns:
        the probability of index.php being available.
        * [0.0 - 0.5) - not available
        * 0.5 - generally not sure
        * (0.5 - 1] - available
    """

    print("Checking index.php...", index)

    r = None

    for page in [
                 "Special:Random",
                 "Special:Version",
                 "Special:AllPages",
                 "Special:ListFiles",
                 "Special:Search",
                 ]:
        print(f"check_index(): Trying {page}...")

        try:
            try:
                r = session.post(url=index, data={"title": page}, timeout=30, allow_redirects=True)
            except requests.exceptions.TooManyRedirects:
                r = session.post(url=index, params={"title": page}, timeout=30, allow_redirects=False)
        except Exception as e:
            print("check_index(): Exception:", e)
            time.sleep(2)
            continue

        for _r in r.history:
            print(_r.request.method, _r.url, {"title": page}, _r.status_code)
        print(r.request.method, r.url, {"title": page}, r.status_code)

        if r.status_code in [301, 302, 303, 307, 308]:
            print("The index.php returned a redirect")
            continue

        if r.status_code >= 400:
            print(f"ERROR: The wiki returned status code HTTP {r.status_code}")
            continue

        break

    if r is None:
        print("ERROR: Failed to get index.php")
        return 0.15
    
    if r.status_code in [301, 302, 303, 307, 308]:
        print("The index.php returned a redirect")
        return 0.3

    raw = r.text
    # Workaround for
    # [Don't try to download private wikis unless --cookies is given]
    # (https://github.com/wikiTeam/wikiteam/issues/71)
    if (
        re.search(
            '(Special:Badtitle</a>|class="permissions-errors"|"wgCanonicalSpecialPageName":"Badtitle"|Login Required</h1>)',
            raw,
        )
        and not logged_in
    ):
        print("ERROR: This wiki requires login and we are not authenticated")
        return 0.5
    if re.search(
        '(page-Index_php|"wgPageName":"Index.php"|"firstHeading"><span dir="auto">Index.php</span>)',
        raw,
    ):
        print("Looks like the page called Index.php, not index.php itself")
        return 0.1
    if re.search(
        '(This wiki is powered by|<h2 id="mw-version-license">|meta name="generator" content="MediaWiki|class="mediawiki)',
        raw,
    ):
        return 0.9

    return 0.2
