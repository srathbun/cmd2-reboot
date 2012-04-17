# -*- coding: UTF-8 -*-
'''Variant on standard library's `cmd` with extra features.

To use, simply `import cmd2.Cmd` instead of `cmd.Cmd`. Use as the standard 
library's cmd, while enjoying the extra features.

    *   Searchable command history (commands: "hi", "li", "run")
    *   Load commands from file, save to file, edit commands in file
    *   Multi-line commands
    *   Case-insensitive commands
    *   Special-character shortcut commands (beyond cmd's "@" and "!")
    *   Settable environment parameters
    *   Optional _onchange_{paramname} called when environment parameter changes
    *   Parsing commands with `optparse` options (flags)
    *   Redirection to file with `>`, `>>`; input from file with `<`
    *   Easy transcript-based testing of applications (see `example/example.py`)
    *   Bash-style `select` available

Note that redirection with `>` and `|` will only work if `self.stdout.write()`
is used in place of `print`.  (The standard library's `cmd` module is 
written to use `self.stdout.write()`).

- Catherine Devlin, Jan 03 2008 - catherinedevlin.blogspot.com

mercurial repository:
    http://www.assembla.com/wiki/show/python-cmd2
'''

from    __future__  import  generators,         \
                            print_function,     \
                            with_statement

import  six

from    optparse    import  make_option

#   Cmd2 Modules
#   --------------------------------------------------------
from    .cmd2       import  Cmd

from    .errors     import (EmbeddedConsoleExit ,
                            EmptyStatement      ,
                            NotSettableError    ,
                            PasteBufferError    ,
                            PASTEBUFF_ERR)

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


__all__         =   ['cmd2', 'Cmd', 'errors', 'support', 'make_option']
    
__package__     =   'cmd2'

__version__     =   '0.6.5'
__copyright__   =   '?'           #@FIXME
__license__     =   '?'           #@FIXME
__status__      =   '4 - Beta'
  
__author__      =   'Catherine Devlin'
__email__       =   'catherine.devlin@gmail.com'
__maintainer__  =   '?'           #@FIXME
__credits__     =   '?'           #@FIXME

