
import warnings

import requests
import pytest
from urllib3.exceptions import InsecureRequestWarning

from wikiteam3.utils.monkey_patch import WakeTLSAdapter

def _get_session():
    session = requests.Session()
    session.verify = False
    requests.packages.urllib3.disable_warnings() # type: ignore
    for protocol in ['http://', 'https://']:
        session.mount(protocol, WakeTLSAdapter())
    return session

session = None

badssl_ok_urls = [
    "https://expired.badssl.com/",
    "https://wrong.host.badssl.com/",
    "https://self-signed.badssl.com/",
    "https://untrusted-root.badssl.com/",
    "https://revoked.badssl.com/",
    "https://pinning-test.badssl.com/",

    "https://no-common-name.badssl.com",
    "https://incomplete-chain.badssl.com",
    "https://no-subject.badssl.com",

    "https://mozilla-old.badssl.com",
    "https://null.badssl.com",

    "https://dh1024.badssl.com",
    "https://dh2048.badssl.com",

    "https://dh-small-subgroup.badssl.com",
    "https://dh-composite.badssl.com",

    "https://tls-v1-0.badssl.com:1010",
    "https://tls-v1-1.badssl.com:1011",
    "https://tls-v1-2.badssl.com:1012",

    "https://no-sct.badssl.com",

    "https://subdomain.preloaded-hsts.badssl.com",
    "https://superfish.badssl.com",
    "https://dsdtestprovider.badssl.com",
    "https://preact-cli.badssl.com",
    "https://webpack-dev-server.badssl.com",

    "https://captive-portal.badssl.com",
    "https://mitm-software.badssl.com",

    "https://sha1-2016.badssl.com",
    "https://sha1-2017.badssl.com",
    "https://sha1-intermediate.badssl.com",
    "https://invalid-expected-sct.badssl.com",

]
@pytest.mark.parametrize("url", badssl_ok_urls)
def test_the_badssl_ok(url):
    global session
    session = session or _get_session()
    resp = None
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",category=InsecureRequestWarning)
        try:
            resp = session.get(url, timeout=20)
        except Exception as e:
            pytest.fail(f"Could not fetch {url}: {e}")

    assert resp is not None, f"Could not fetch {url}"

badssl_may_fail_urls = [
    "https://rc4-md5.badssl.com",
    "https://rc4.badssl.com",
    "https://3des.badssl.com",

    "https://dh480.badssl.com",
    "https://dh512.badssl.com",
]
@pytest.mark.parametrize("url", badssl_may_fail_urls)
def test_the_badssl_may_fail(url):
    global session
    session = session or _get_session()
    resp = None
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",category=InsecureRequestWarning)
        try:
            resp = session.get(url, timeout=20)
        except Exception as e:
            pytest.skip("This test is expected to fail on default OpenSSL configuration")
