from typing import Dict, Optional
import xml.etree.ElementTree as ET

from lxml import etree
from lxml.builder import E

from wikiteam3.dumpgenerator.exceptions import PageMissingError

def make_xml_page_from_raw(xml: str, arvcontinue: Optional[str] = None) -> str:
    """Discard the metadata around a <page> element in <mediawiki> string

    arvcontinue: None -> disable arvcontinue (default)
    arvcontinue: string (including empty "") -> write arvcontinue to XML (for api:allrevisions resuming)
    """
    tree: ET.Element = ET.XML(xml)
    page: ET.Element | None = tree.find(".//{*}page")

    assert page is not None

    if arvcontinue is not None:
        page.attrib['arvcontinue'] = arvcontinue
    # remove namespace prefix
    for elem in tree.iter():
        elem.tag = elem.tag.split('}', 1)[-1]

    return ET.tostring(page, encoding="unicode", method="xml", xml_declaration=False)


def make_xml_from_page(page: Dict, arvcontinue: Optional[str] = None) -> str:
    """Output an XML document as a string from a page as in the API JSON

    arvcontinue: None -> disable arvcontinue (default)
    arvcontinue: string (including empty "") -> write arvcontinue to XML (for api:allrevisions resuming)
    """
    try:
        p = E.page(
            E.title(str(page["title"])),
            E.ns(str(page["ns"])),
            E.id(str(page["pageid"])),
        )
        if arvcontinue is not None:
            p.attrib['arvcontinue'] = arvcontinue
        for rev in page["revisions"]:
            # Older releases like MediaWiki 1.16 do not return all fields.
            if "userid" in rev:
                userid = rev["userid"]
            else:
                userid = 0
            if "size" in rev:
                size = rev["size"]
            else:
                size = 0

            # Create rev object
            revision = [E.id(str(rev["revid"])),
                E.timestamp(rev["timestamp"]),]

            # The text, user, comment, sha1 may be deleted/suppressed
            if (('texthidden' in rev) or ('textmissing' in rev)) or ('*' not in rev):
                print("Warning: text missing/hidden in pageid %d revid %d" % (page['pageid'], rev['revid']))
                revision.append(E.text(**{
                    'bytes': str(size),
                    'deleted': 'deleted',
                }))
            else:
                text = str(rev["*"])
                revision.append(E.text(text, **{
                    'bytes': str(size),
                    '{http://www.w3.org/XML/1998/namespace}space': 'preserve',
                }))

            if "user" not in rev:
                if "userhidden" not in rev:
                    print("Warning: user not hidden but missing user in pageid %d revid %d" % (page['pageid'], rev['revid']))
                revision.append(E.contributor(deleted="deleted"))
            else:
                revision.append(
                    E.contributor(
                        E.username(str(rev["user"])),
                        E.id(str(userid)),
                    )
                )

            if "sha1" not in rev:
                if "sha1hidden" in rev:
                    revision.append(E.sha1()) # stub
                else:
                    # The sha1 may not have been backfilled on older wikis or lack for other reasons (Wikia).
                    pass
            elif "sha1" in rev:
                revision.append(E.sha1(rev["sha1"]))


            if 'commenthidden' in rev:
                revision.append(E.comment(deleted="deleted"))
            elif "comment" in rev and rev["comment"]:
                revision.append(E.comment(str(rev["comment"])))

            if "contentmodel" in rev:
                revision.append(E.model(rev["contentmodel"]))
            if "contentformat" in rev:
                revision.append(E.format(rev["contentformat"]))
            if "parentid" in rev and int(rev["parentid"]) > 0:
                revision.append(E.parentid(str(rev["parentid"])))

            if "minor" in rev:
                revision.append(E.minor())

            # mwcli's dump.xml order
            revisionTags = ['id', 'parentid', 'timestamp', 'contributor', 'minor', 'comment', 'origin', 'model', 'format', 'text', 'sha1']
            revisionElementsDict = {elem.tag: elem for elem in revision}
            _revision = E.revision()
            for tag in revisionTags:
                if tag in revisionElementsDict:
                    _revision.append(revisionElementsDict.pop(tag))
            for elem in revisionElementsDict.values():
                _revision.append(elem)
            p.append(_revision)
    except KeyError as e:
        import traceback
        traceback.print_exc()
        raise PageMissingError(page["title"], e)
    return etree.tostring(p, pretty_print=True, encoding="unicode")
