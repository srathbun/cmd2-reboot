# -*- coding: UTF-8 -*-


from    __future__  import  generators,         \
                            print_function,     \
                            with_statement

import  six


#   Cmd2 Modules
#   --------------------------------------------------------
import  cmd2
from    .cmd2        import (Cmd            ,
                            OptionParser    ,
                            ParsedString    , 
                            remaining_args  )

from    .errors     import (EmbeddedConsoleExit ,
                            EmptyStatement      ,
                            NotSettableError    ,
                            PasteBufferError)

from    .parsers    import (OptionParser,
                            ParsedString,
                            remaining_args,
                            options     ,
                            options_defined)
                            
from    .support    import (HistoryItem ,
                            History     ,
                            Statekeeper ,
                            StubbornDict,
                            stubbornDict,
                            cast        ,
                            ljust       ,
                            pastebufferr,
                            replace_with_file_contents)
                            
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


__all__         =   ['cmd2', 'errors', 'support']
    
__package__     =   'cmd2'

__version__     = '0.6.5'
__copyright__   = '?'           #@FIXME
__license__     = '?'           #@FIXME
__status__      = '4 - Beta'

__author__      = 'Catherine Devlin'
__email__       = 'catherine.devlin@gmail.com'
__maintainer__  = '?'           #@FIXME
__credits__     = '?'           #@FIXME

