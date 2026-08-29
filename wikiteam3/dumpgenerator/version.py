__VERSION__ = "unknown"

try:
    import importlib.metadata
    __VERSION__ = importlib.metadata.version("wikiteam3")
except Exception:
    pass


def get_version():
    return __VERSION__
