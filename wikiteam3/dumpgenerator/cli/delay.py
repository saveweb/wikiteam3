import itertools
import threading
import time
from typing import Optional

from wikiteam3.dumpgenerator.config import Config


class Delay:
    done: bool = False
    lock: threading.Lock = threading.Lock()

    def animate(self):
        progress_dots = itertools.cycle([".", "/", "-", "\\"])
        for dot in progress_dots:
            with self.lock:
                if self.done:
                    return

                print("\r" + self.ellipses, end=dot)

            time.sleep(0.3)

    def __init__(self, config: Optional[Config]=None, msg: Optional[str]=None, delay: Optional[float]=None):
        """Add a delay if configured for that
        
        if delay is None, use config.delay
        """

        if delay is None:
            assert isinstance(config, Config)
            delay = config.delay
        if delay <= 0:
            return

        if msg:
            self.ellipses = ("Delay %.1fs: %s " % (delay, msg))
        else:
            self.ellipses = ("Delay %.1fs" % (delay))

        ellipses_animation = threading.Thread(target=self.animate)
        ellipses_animation.daemon = True
        ellipses_animation.start()

        time.sleep(delay)

        with self.lock:
            self.done = True
            print("\r" + " " * len(self.ellipses), end=" \r")
