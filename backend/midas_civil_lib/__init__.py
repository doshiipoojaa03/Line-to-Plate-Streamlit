import requests
from ._mapi import *
_version_ = "STREAMLIT"


print('')
print('*'*20,'  MIDAS CIVIL-NX PYTHON LIBRARY v',_version_,' 🐍 ','*'*20)
print('')

# if NX.version_check:
#     resp =  requests.get("https://pypi.org/pypi/midas_civil/json").json()
#     latest_ver =  resp["info"]["version"]
#     if _version_ != latest_ver:
#         print(
#                 f"⚠️  Warning: You are using v{_version_}, "
#                 f"but the latest available version is v{latest_ver}.\n"
#                 f" Run 'pip install midas_civil --upgrade' to update."
#             )
#         print("-"*85)


from ._boundary import *
from ._utils import *
from ._node import *
from ._element import *

from ._group import *


#--- TESTING IMPORTS ---


# from ._section import *
from ._section import *


from ._thickness import *





