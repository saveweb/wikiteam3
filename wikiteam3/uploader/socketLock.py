
import itertools
import socket
import time


class SocketLockServer:
    """A server that binds to a port and holds it until released."""
    HOST, PORT = "localhost", 62954

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def try_bind(self, strict=False):
        try:
            self._socket.bind((self.HOST, self.PORT))
        except OSError:
            # Port is in use
            if strict:
                raise
            return False
        
        print(f"SocketServer: Listening on {self.HOST}:{self.PORT}")
        return True

    def is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.HOST, self.PORT)) == 0


    def bind_until_port_is_free(self):
        dots = ["/", "-", "\\", "|"]
        for dot in itertools.cycle(dots):
            if not self.is_port_in_use():
                if self.try_bind():
                    return True
            time.sleep(0.5)
            print(f"{self.HOST}:{self.PORT} is in use, waiting {dot}", end="\r")

    def release(self):
        if not self._socket._closed: # type: ignore
            self._socket.close()
            print(f"SocketServer: Released {self.HOST}:{self.PORT}")
            return True
        print(f"SocketServer: No need to release {self.HOST}:{self.PORT}")
        return None

    def __enter__(self):
        self.bind_until_port_is_free()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


class NoLock:
    def __init__(self):
        pass

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return None
