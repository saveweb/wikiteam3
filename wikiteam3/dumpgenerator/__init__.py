from pathlib import Path
from wikiteam3.dumpgenerator.dump import DumpGenerator

DUMPER_ROOT_PATH = Path(__file__).parent

def main():
    DumpGenerator()
