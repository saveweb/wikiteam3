from pathlib import Path
from wikiteam3.dumpgenerator.dump import DumpGenerator

DUMPER_ROOT_PATH = Path(__file__).parent

def main():
    DumpGenerator()


def main_deprecated(): # poetry scripts dumpgenerator = "wikiteam3.dumpgenerator:main_deprecated"
    import warnings
    warnings.warn("dumpgenerator is deprecated, use wikiteam3dumpgenerator instead", DeprecationWarning)
    main()
