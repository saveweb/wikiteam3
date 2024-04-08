import os
import ssl
import time
from typing import Optional
import warnings

import requests
import requests.adapters
from urllib3.util import create_urllib3_context
from urllib3 import PoolManager

from wikiteam3.dumpgenerator.cli.delay import Delay
from wikiteam3.dumpgenerator.config import Config

def mod_requests_text(requests: requests): # type: ignore
    """ 
    - Monkey patch `requests.Response.text` to handle incorrect encoding.
    - Replace error characters with � (U+FFFD) if them are not too many. ($WIKITEAM3_REQUESTS_TEXT_FFFD_TOLERANCE)
    """
    def new_text(_self: requests.Response):
        # Handle incorrect encoding
        encoding = _self.encoding
        if encoding is None or encoding == 'ISO-8859-1':
            encoding = _self.apparent_encoding
            if encoding is None:
                encoding = 'utf-8'
        if _self.content.startswith(b'\xef\xbb\xbf'):
            content = _self.content.lstrip(b'\xef\xbb\xbf')
            encoding = "utf-8"
        else:
            content = _self.content

        try:
            return content.decode(encoding, errors="strict")
        except UnicodeDecodeError as e:
            FFFD_CHAR = u'�'
            FFFD_TOLERANCE = float(os.environ.get('WIKITEAM3_REQUESTS_TEXT_FFFD_TOLERANCE', '0.01'))
            assert 0 <= FFFD_TOLERANCE <= 1
            print('UnicodeDecodeError:', e)
            ignore_text = content.decode(encoding, errors='ignore')
            FFFDs_in_ignore_text = ignore_text.count(FFFD_CHAR)
            replace_text = content.decode(encoding, errors='replace')
            FFFDs_in_replace_text = replace_text.count(FFFD_CHAR)
            
            bad_FFFDs = FFFDs_in_replace_text - FFFDs_in_ignore_text
            bad_FFFDs_ratio = bad_FFFDs / len(replace_text)

            if bad_FFFDs_ratio > FFFD_TOLERANCE:
                print(f"ERROR: Bad \\ufffd too many. {bad_FFFDs} bad FFFDs in {len(replace_text)} chars ({bad_FFFDs_ratio}) "
                      "Check the encoding or set $WIKITEAM3_REQUESTS_TEXT_FFFD_TOLERANCE to a higher value.")
                raise e

            warnings.warn(
                message=f"found bad \\ufffd, but tolerable. {bad_FFFDs} bad FFFDs in {len(replace_text)} chars ({bad_FFFDs_ratio})",
                category=UserWarning
            )
            return replace_text


    requests.Response.text = property(new_text) # type: ignore


class WakeTLSAdapter(requests.adapters.HTTPAdapter):
    """
    Workaround for bad SSL/TLS
    """
    def init_poolmanager(self, connections, maxsize, block=False):
        # https://www.openssl.org/docs/manmaster/man1/openssl-ciphers.html
        ctx = create_urllib3_context(ciphers="ALL:COMPLMENTOFDEFAULT:eNULL:@SECLEVEL=0")

        ctx.options &= ~ssl.OP_NO_TLSv1_3 & ~ssl.OP_NO_TLSv1_2 & ~ssl.OP_NO_TLSv1_1 & ~ssl.OP_NO_TLSv1
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",category=DeprecationWarning)
            ctx.minimum_version = ssl.TLSVersion.TLSv1

        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

class SessionMonkeyPatch:
    """
    Monkey patch `requests.Session.send`
    """
    hijacked = False
    def __init__(self,*, session: requests.Session, config: Optional[Config]=None,
                 add_delay: bool=False, delay_msg: Optional[str]=None,
                 hard_retries: int=0,
                 free_timeout_connections: bool=True, vaild_lft_sec: int=60 * 3,
                 accept_encoding: str="",
        ):
        """
        hard_retries: hard retries, default 0 (no retry)
        free_timeout_connections: regularly(`vaild_lft_sec`) clear connections pool
        """

        self.session = session
        self.config = config

        self.add_delay = add_delay
        self.delay_msg = delay_msg

        self.hard_retries = hard_retries

        self.free_timeout_connections: bool = free_timeout_connections
        self.vaild_lft_sec = vaild_lft_sec
        self.last_clear_time = time.time()

        self.accept_encoding = accept_encoding

    def clear_timeouted_pools(self):
        for adapter in self.session.adapters.values():
            adapter: requests.adapters.HTTPAdapter
            if adapter.poolmanager.pools._container.__len__() > 0 and \
                time.time() - self.last_clear_time > self.vaild_lft_sec:
                # TODO: logging this
                # print('Keep-alived timeout: %d' % adapter.poolmanager.pools._container.__len__(), "connection(s) dropped.")
                adapter.poolmanager.clear() # clear all
                self.last_clear_time = time.time()

    def hijack(self):
        ''' Don't forget to call `release()` '''

        # Monkey patch `requests.Session.send`
        self.old_send_method = self.session.send

        def new_send(request: requests.PreparedRequest, **kwargs):
            hard_retries_left = self.hard_retries + 1
            if hard_retries_left <= 0:
                raise ValueError('hard_retries must be positive')

            accept_encoding = ''

            while hard_retries_left > 0:
                try:
                    if self.add_delay:
                        Delay(msg=self.delay_msg, config=self.config)

                    if self.free_timeout_connections:
                        self.clear_timeouted_pools()

                    if _accept_encoding := accept_encoding or self.accept_encoding or request.headers.get("Accept-Encoding", ""):
                        request.headers["Accept-Encoding"] = _accept_encoding

                    return self.old_send_method(request, **kwargs)
                except (KeyboardInterrupt, requests.exceptions.ContentDecodingError): # don't retry
                    raise
                except Exception as e:
                    hard_retries_left -= 1
                    if hard_retries_left <= 0:
                        raise

                    print('Hard retry... (%d), due to: %s' % (hard_retries_left, e))

                    # workaround for https://wiki.erischan.org/index.php/Main_Page and other ChunkedEncodingError sites
                    if isinstance(e, requests.exceptions.ChunkedEncodingError):
                        accept_encoding = 'identity'
                        print('retry with Accept-Encoding:', accept_encoding)

                    # if --bypass-cdn-image-compression is enabled, retry with different url
                    assert isinstance(request.url, str)
                    if '_wikiteam3_nocdn=' in request.url:
                        request.url = request.url.replace('_wikiteam3_nocdn=init_req', f'_wikiteam3_nocdn=retry_{hard_retries_left}')
                        request.url = request.url.replace(
                            f'_wikiteam3_nocdn=retry_{hard_retries_left + 1}',
                            f'_wikiteam3_nocdn=retry_{hard_retries_left}'
                            )
                        print('--bypass-cdn-image-compression: change url to', request.url, 'on hard retry...')

                    time.sleep(3)

        self.session.send = new_send # type: ignore
        self.hijacked = True

    def release(self):
        ''' Undo monkey patch '''
        if not self.hijacked:
            warnings.warn('Warning: SessionMonkeyPatch.release() called before hijack()', RuntimeWarning)
            return
        self.session.send = self.old_send_method
        del self

    def __del__(self):
        if self.hijacked:
            print('Undo monkey patch...')
            self.release()
