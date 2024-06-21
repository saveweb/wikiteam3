from .util import remove_IP, clean_XML, clean_HTML, undo_HTML_entities, sha1sum

from .user_agent import get_random_UserAgent
from .identifier import url2prefix_from_config
from .wiki_avoid import avoid_WikiMedia_projects
from .monkey_patch import mod_requests_text
from .login import uniLogin, fetch_login_token, bot_login, client_login, index_login