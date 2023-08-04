import re
from urllib.parse import urlparse, unquote

from slugify import slugify

from wikiteam3.dumpgenerator.config import Config


def url2prefix_from_config(config: Config, ascii_slugify: bool = True):
    """
    Chose a filename/dirname prefix for the dump based on the API url or INDEX url in the config.

    see `url2prefix()` for details
    """

    if url := config.api:
        return url2prefix(url, ascii_slugify=ascii_slugify)
    elif url := config.index:
        return url2prefix(url, ascii_slugify=ascii_slugify)
    else:
        raise ValueError('No URL found in config')


def standardize_url(url: str, strict: bool = True):
    """ 1. strip and unquote url
            > raises ValueError if url contains newline (`\\n` or `\\r`) after stripping
        2. Add `http://` if scheme is missing
            > if `strict` is True, raises ValueError if scheme is missing
        3. Convert domain to IDNA
        4. Remove port `:80` and `:443` if `http://` and `https://` respectively
    """
    # TODO: make step 1,2,4 optional and reversible

    url = url.strip()
    if '\n' in url or '\r' in url:
        raise ValueError('URL contains newline')
    url = unquote(url, encoding='utf-8', errors='strict')

    if not url.startswith('http://') and not url.startswith('https://'):
        if strict:
            raise ValueError(f'HTTP(s) scheme is missing: {url}') 
        print('Warning: URL scheme is missing, assuming http://')
        url = 'http://' + url

    Url = urlparse(url)
    idna_hostname = Url.hostname.encode('idna').decode('utf-8')

    if Url.hostname != idna_hostname:
        print('Converting domain to IDNA: ' + Url.hostname + ' -> ' + idna_hostname)
        url = url.replace(Url.hostname, idna_hostname, 1)
    
    if Url.port == 80 and Url.scheme == 'http':
        print('Removing port 80 from URL')
        url = url.replace(':80', '', 1)
    
    if Url.port == 443 and Url.scheme == 'https':
        print('Removing port 443 from URL')
        url = url.replace(':443', '', 1)

    return url


def url2prefix(url: str, ascii_slugify: bool = True):
    """Convert URL to a valid prefix filename.
    
    1. standardize url (see `standardize_url()`)
    2. remove last slash if exists
    3. truncate to last slash
    4. remove "/any.php" suffix
    5. remove ~ tilde
    6. sulgify the url path if `ascii_slugify` is True
    7. replace port(`:`) with underscore(`_`)
    8. lower case

    """

    url = standardize_url(url)

    r = urlparse(url)

    r_path = r.path

    if r.path.endswith('/'):
        # remove last slash
        # "/abc/123/" -> "/abc/123"
        # "/" -> ""
        r_path = r.path[:-1]
    else: # not r.path.endswith('/')
        # truncate to last slash
        # "/abc/123/edf" -> "/abc/123"
        r_path =  r.path[:r.path.rfind('/')]

    # remove "/any.php" suffix
    r_path = re.sub(r"(/[^/]+\.php)", "", r_path)
    # remove tilde
    r_path = r_path.replace('~', '')
    # sulgify
    _r_paths = r_path.split('/')
    if ascii_slugify:
        _r_paths = [slugify(p, separator='_', allow_unicode=False) for p in _r_paths]
    r_path = '_'.join(_r_paths)

    # replace port with underscore
    r_netloc = r.netloc.replace(':', '_')

    # lower case
    prefix = (r_netloc + r_path).lower()
    assert prefix == prefix.strip('_'), 'prefix contains leading or trailing underscore, please report this bug.'

    return prefix
