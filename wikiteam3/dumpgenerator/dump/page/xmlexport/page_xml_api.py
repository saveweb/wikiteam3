import re
import time
import traceback
from typing import Dict, Optional
import xml.etree.ElementTree as ET
import xml.dom.minidom as MD

import requests

from wikiteam3.dumpgenerator.api import handle_StatusCode
from wikiteam3.dumpgenerator.config import Config
from wikiteam3.dumpgenerator.exceptions import PageMissingError, ExportAbortedError
from wikiteam3.dumpgenerator.log import log_error
from wikiteam3.utils.util import underscore


def reconstructRevisions(root: ET.Element):
    #print ET.tostring(rev)
    page = ET.Element('stub')
    edits = 0

    if root.find('query').find('pages').find('page').find('revisions') is None: # type: ignore
        # case: https://wiki.archlinux.org/index.php?title=Arabic&action=history
        # No matching revisions were found.
        print('!!! No revisions found in page !!!')
        return page, edits # no revisions

    for rev in root.find('query').find('pages').find('page').find('revisions').findall('rev'): # type: ignore
        try:
            rev_ = ET.SubElement(page,'revision')
            # id
            ET.SubElement(rev_,'id').text = rev.attrib['revid']
            # parentid (optional, export-0.7+, positiveInteger)
            if 'parentid' in rev.attrib and int(rev.attrib['parentid']) > 0:
                ET.SubElement(rev_,'parentid').text = rev.attrib['parentid'] 
            # timestamp
            ET.SubElement(rev_,'timestamp').text = rev.attrib['timestamp']
            # contributor
            contributor = ET.SubElement(rev_,'contributor')
            if 'userhidden' not in rev.attrib:
                ET.SubElement(contributor,'username').text = rev.attrib['user']
                ET.SubElement(contributor,'id').text = rev.attrib['userid']
            else:
                contributor.set('deleted','deleted')
            # comment (optional)
            if 'commenthidden' in rev.attrib:
                print('commenthidden')
                comment = ET.SubElement(rev_,'comment')
                comment.set('deleted','deleted')
            elif 'comment' in rev.attrib and rev.attrib['comment']: # '' is empty
                comment = ET.SubElement(rev_,'comment')
                comment.text = rev.attrib['comment']
            else:
                # no comment or empty comment, do not create comment element
                pass

            # minor edit (optional)
            if 'minor' in rev.attrib:
                ET.SubElement(rev_,'minor')
            # model and format (optional, export-0.8+)
            if 'contentmodel' in rev.attrib:
                ET.SubElement(rev_,'model').text = rev.attrib['contentmodel'] # default: 'wikitext'
            if 'contentformat' in rev.attrib:
                ET.SubElement(rev_,'format').text = rev.attrib['contentformat'] # default: 'text/x-wiki'
            # text
            text = ET.SubElement(rev_,'text')
            if 'texthidden' not in rev.attrib:
                text.attrib['xml:space'] = "preserve"
                text.attrib['bytes'] = rev.attrib['size']
                text.text = rev.text
            else:
                # NOTE: this is not the same as the text being empty
                text.set('deleted','deleted')
            # sha1
            if 'sha1' not in rev.attrib:
                if 'sha1hidden' in rev.attrib:
                    ET.SubElement(rev_,'sha1') # stub
                else:
                    # The sha1 may not have been backfilled on older wikis or lack for other reasons (Wikia).
                    pass
            elif 'sha1' in rev.attrib:
                sha1 = ET.SubElement(rev_,'sha1')
                sha1.text = rev.attrib['sha1']
            
            edits += 1
        except Exception as e:
            #logerror(config=config, text='Error reconstructing revision, xml:%s' % (ET.tostring(rev)))
            print(ET.tostring(rev))
            traceback.print_exc()
            page = None
            edits = 0
            raise e
    return page,edits

def getXMLPageCoreWithApi(config: Config, session: requests.Session, params: Dict, headers: Optional[Dict]=None):
    """  """
    # just send the API request
    # if it fails, it will reduce params['rvlimit']
    xml = ''
    c = 0
    maxseconds = 100  # max seconds to wait in a single sleeping
    maxretries = config.retries  # x retries and skip
    increment = 20  # increment every retry

    while not re.search(r'</api>' if not config.curonly else r'</mediawiki>', xml) or re.search(r'</error>', xml):
        if c > 0 and c < maxretries:
            wait = increment * c < maxseconds and increment * \
                   c or maxseconds  # incremental until maxseconds
            print('    In attempt %d, XML for "%s" is wrong. Waiting %d seconds and reloading...' % (
            c, params['titles' if config.xmlapiexport else 'pages'], wait))
            time.sleep(wait)
            # reducing server load requesting smallest chunks (if curonly then
            # rvlimit = 1 from mother function)
            if params['rvlimit'] > 1:
                rvlimit = int(params['rvlimit'] / 2)  # half
                params['rvlimit'] = rvlimit if rvlimit > 1 else 1
            print('    We have retried %d times' % (c))
            print('    MediaWiki error for "%s", network error or whatever...' % (
            params['titles' if config.xmlapiexport else 'pages']))
            # If it's not already what we tried: our last chance, preserve only the last revision...
            # config.curonly means that the whole dump is configured to save only the last,
            # params['curonly'] should mean that we've already tried this
            # fallback, because it's set by the following if and passed to
            # getXMLPageCore
            # TODO: save only the last version when failed
            print('    Saving in the errors log, and skipping...')
            log_error(
                config=config,
                text='Error while retrieving the last revision of "%s". Skipping.' %
                     (params['titles' if config.xmlapiexport else 'pages']))
            raise ExportAbortedError(config.index)
            return ''  # empty xml

        # FIXME HANDLE HTTP Errors HERE
        try:
            r = session.get(url=config.api, params=params, headers=headers)
            handle_StatusCode(r)
            xml = r.text
            # print xml
        except requests.exceptions.ConnectionError as e:
            print('    Connection error: %s' % (str(e.args[0])))
            xml = ''
        except requests.exceptions.ReadTimeout as e:
            print("    Read timeout: %s" % (str(e.args[0])))
            xml = ""
        c += 1
    return xml


def getXMLPageWithApi(config: Config, title="", verbose=True, *, session: requests.Session):
    """ Get the full history (or current only) of a page using API:Query
        if params['curonly'] is set, then using export&exportwrap to export
    """

    title_ = underscore(title)
    # do not convert & into %26, title_ = re.sub('&', '%26', title_)
    # action=query&rvlimit=50&format=xml&prop=revisions&titles=TITLE_HERE
    # &rvprop=timestamp%7Cuser%7Ccomment%7Ccontent%7Cids%7Cuserid%7Csha1%7Csize
    # print 'current:%s' % (title_)
    if not config.curonly:
        params = {'titles': title_, 'action': 'query', 'format': 'xml',
                  'prop': 'revisions',
                  'rvprop': # rvprop: <https://www.mediawiki.org/wiki/API:Revisions#Parameter_history>
                            '|'.join([
                                'timestamp', 'user', 'comment', 'content', # MW v????
                                'ids', 'flags', 'size', # MW v1.11
                                'userid', # MW v1.17
                                'sha1', # MW v1.19
                                'contentmodel' # MW v1.21
                             ]),
                  'rvcontinue': None,
                  'rvlimit': config.api_chunksize
                  }
    else:
        params = {'titles': title_, 'action': 'query', 'format': 'xml', 'export': 1, 'exportnowrap': 1}
    # print 'params:%s' % (params)
    if not config.curonly:
        firstpartok = False
        lastcontinue = None
        numberofedits = 0
        ret = ''
        continueKey: Optional[str] = None

        retries_left = config.retries
        while True:
            if retries_left <= 0:
                raise RuntimeError("Retries exceeded")
            # in case the last request is not right, saving last time's progress
            if not firstpartok:
                lastcontinue = params.get(continueKey, None) if continueKey is not None else None

            xml = getXMLPageCoreWithApi(params=params, config=config, session=session)
            if xml == "":
                # just return so that we can continue, and getXMLPageCoreWithApi will log the error
                return
            try:
                root = ET.fromstring(xml.encode('utf-8'))
            except Exception as e:
                retries_left -= 1
                traceback.print_exc()
                print("Retrying...")
                continue
            try:
                retpage = root.find('query').find('pages').find('page') # type: ignore
            except Exception:
                retries_left -= 1
                traceback.print_exc()
                print("Retrying...")
                continue

            assert retpage is not None, "Should have a page"

            if 'missing' in retpage.attrib or 'invalid' in retpage.attrib:
                print('Page not found')
                raise PageMissingError(params['titles'], xml)
            if not firstpartok:
                try:
                    # build the firstpart by ourselves to improve the memory usage
                    ret = '  <page>\n'
                    ret += '    <title>%s</title>\n' % (retpage.attrib['title'])
                    ret += '    <ns>%s</ns>\n' % (retpage.attrib['ns'])
                    ret += '    <id>%s</id>\n' % (retpage.attrib['pageid'])
                except Exception:
                    firstpartok = False
                    retries_left -= 1
                    traceback.print_exc()
                    print("Retrying...")
                    continue
                else:
                    firstpartok = True
                    yield ret

            # find the continue key
            continueVal = None
            if root.find('continue') is not None:
                # uses continue.rvcontinue
                # MW 1.26+
                continueKey = 'rvcontinue'
                continueVal = root.find('continue').attrib['rvcontinue'] # type: ignore
            elif root.find('query-continue') is not None:
                revContinue = root.find('query-continue').find('revisions') # type: ignore
                assert revContinue is not None, "Should only have revisions continue"
                if 'rvcontinue' in revContinue.attrib:
                    # MW 1.21 ~ 1.25
                    continueKey = 'rvcontinue'
                    continueVal = revContinue.attrib['rvcontinue']
                elif 'rvstartid' in revContinue.attrib:
                    # TODO: MW ????
                    continueKey = 'rvstartid'
                    continueVal = revContinue.attrib['rvstartid']
                else:
                    # blindly assume the first attribute is the continue key
                    # may never happen
                    assert len(revContinue.attrib) > 0, "Should have at least one attribute"
                    for continueKey in revContinue.attrib.keys():
                        continueVal = revContinue.attrib[continueKey]
                        break
            if continueVal is not None:
                params[continueKey] = continueVal

            # build the revision tags
            try:
                ret = ''
                edits = 0

                # transform the revision
                rev_, edits = reconstructRevisions(root=root)
                numberofedits += edits
                xmldom = MD.parseString(b'<stub1>' + ET.tostring(rev_) + b'</stub1>')
                # convert it into text in case it throws MemoryError
                # delete the first three line and last two line,which is for setting the indent
                ret += ''.join(xmldom.toprettyxml(indent='  ').splitlines(True)[3:-2])
                yield ret
                if config.curonly or continueVal is None:  # no continue
                    break
            except Exception:
                retries_left -= 1
                traceback.print_exc()
                print("Retrying...")
                params['rvcontinue'] = lastcontinue
                ret = ''
        yield '  </page>\n'
        if numberofedits == 0:
            raise PageMissingError(title=title_, xml=xml)
    else: # curonly
        xml = getXMLPageCoreWithApi(params=params, config=config, session=session)
        if xml == "":
            raise ExportAbortedError(config.index)
        if "</page>" not in xml:
            raise PageMissingError(title_, xml)

        yield xml.split("</page>")[0]

        # just for looking good :)
        r_timestamp = r'<timestamp>([^<]+)</timestamp>'

        numberofedits = 0
        numberofedits += len(re.findall(r_timestamp, xml))

        yield "</page>\n"

    if verbose:
        if (numberofedits == 1):
            print('    %s, 1 edit' % (title.strip()))
        else:
            print('    %s, %d edits' % (title.strip(), numberofedits))
