import os
import gettext

from enum import Enum

EProdtype = Enum('EProdtype', ['debug', 'prod'])

prodtype = EProdtype.prod

EModetype = Enum('EModetype', ['install', 'upgrade'])

mode = EModetype.install

os.environ['LANGUAGE']='en'

cwd = os.getcwd()
localesPath = os.path.join(cwd, 'locales')
tr = gettext.translation('icw', localesPath)

_ = None
if tr :
    _ = tr.gettext
else :
    _ = gettext.gettext
# from icwconfig import _

lastWord = ''