import argparse

from wikiteam3.dumpgenerator.dump.xmldump.xml_truncate import parse_last_page_chunk, truncateXMLDump

def parse_args():
    parser = argparse.ArgumentParser(description="Get the next arvcontinue value")
    parser.add_argument("xml", help="XML file")
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    xmlfile: str = args.xml
    lastPageChunk = truncateXMLDump(xmlfile, dryrun=True)
    lastPage = parse_last_page_chunk(lastPageChunk)
    assert lastPage is not None
    lastArvcontinue = lastPage.attrib['arvcontinue']
    print(f'ARVCONTINUE="{lastArvcontinue}"')

if __name__ == "__main__":
    main()