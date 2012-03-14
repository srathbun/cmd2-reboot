# -*- coding: UTF-8 -*-


from    __future__  import  generators,         \
                            print_function,     \
                            with_statement

import  six

import  cmd2
from    cmd2    import  Cmd, ParsedString, remaining_args
from    cmd2    import  (History, 
                         HistoryItem,
                         stubbornDict,
                         StubbornDict)

#-------------------------------------------
#   RESERVED:
#   Put initialization-related 
#   Py3 compatibility here.
#-------------------------------------------
# if six.PY3:
#     pass
# else
#     pass
#-------------------------------------------


__all__         =   ['cmd2']
    
__package__     =   'cmd2'

__version__     = '0.6.5'
__copyright__   = '?'           #@FIXME
__license__     = '?'           #@FIXME
__status__      = '4 - Beta'

__author__      = 'Catherine Devlin'
__email__       = 'catherine.devlin@gmail.com'
__maintainer__  = '?'           #@FIXME
__credits__     = '?'           #@FIXME

