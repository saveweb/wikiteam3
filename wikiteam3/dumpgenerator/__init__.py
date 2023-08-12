from wikiteam3.dumpgenerator.dump import DumpGenerator


def main():
    DumpGenerator()


def main_deprecated(): # poetry scripts dumpgenerator = "wikiteam3.dumpgenerator:main_deprecated"
    import warnings
    warnings.warn("dumpgenerator is deprecated, use wikiteam3dumpgenerator instead", DeprecationWarning)
    main()
