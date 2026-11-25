import pytest

from wikiteam3.dumpgenerator.exceptions import UnknownContentModelError

# mwclient.errors.APIError:
#  ('internal_api_error_MediaWiki\\Content\\UnknownContentModelException',
#  '[...] Caught exception of type MediaWiki\\Content\\UnknownContentModelException', None)
@pytest.mark.parametrize("code", [r'internal_api_error_MediaWiki\Content\UnknownContentModelException'])
def test_UnknownContentModelError(code: str):
    assert UnknownContentModelError.match(code)
