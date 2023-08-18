import time
from typing import Optional
import warnings

import requests
import requests.adapters

from wikiteam3.dumpgenerator.cli.delay import Delay
from wikiteam3.dumpgenerator.config import Config

def mod_requests_text(requests: requests): # type: ignore
    """ Monkey patch `requests.Response.text` to handle incorrect encoding """
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

        return content.decode(encoding)

    requests.Response.text = property(new_text) # type: ignore


class SessionMonkeyPatch:
    """
    Monkey patch `requests.Session.send`
    """
    hijacked = False
    def __init__(self,*, session: requests.Session, config: Config,
                 add_delay: bool=False, delay_msg: Optional[str]=None,
                 hard_retries: int=0,
                 free_timeout_connections: bool=True, vaild_lft_sec: int=60 * 3
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

        def new_send(request, **kwargs):
            hard_retries_left = self.hard_retries + 1
            if hard_retries_left <= 0:
                raise ValueError('hard_retries must be positive')

            while hard_retries_left > 0:
                try:
                    if self.add_delay:
                        Delay(msg=self.delay_msg, config=self.config)

                    if self.free_timeout_connections:
                        self.clear_timeouted_pools()

                    return self.old_send_method(request, **kwargs)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    hard_retries_left -= 1
                    if hard_retries_left <= 0:
                        raise

                    print('Hard retry... (%d), due to: %s' % (hard_retries_left, e))
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
