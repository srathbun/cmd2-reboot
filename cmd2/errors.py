# -*- coding: UTF-8 -*-
#   @FIXME
#       Add docstring

#   __future__ first
from    __future__  import  generators,         \
                            print_function,     \
                            with_statement


#   six: Python 2/3 Compatibility module
#   --------------------------------------------------------
#   Six should (after __future__) get imported first,
#   because it deals with the different standard libraries
#   between Python 2 and 3.
import  six


#   @TODO
#       Implement warnings
#import warnings

import  sys,        \
        traceback

__version__     = '0.6.5'
__copyright__   = '?'   #@FIXME
__license__     = '?'   #@FIXME
__status__      = '?'   #@FIXME

__author__      = 'Catherine Devlin'
__email__       = '?'   #@FIXME
__maintainer__  = '?'   #@FIXME
__credits__     = '?'   #@FIXME


__all__         =   [   'EmbeddedConsoleExit',
                        'EmptyStatement',
                        'NotSettableError',
                        'PasteBufferError',
                        'PASTEBUFF_ERR']


PASTEBUFF_ERR =  ''' Redirecting to or from paste buffer requires %s
                    to be installed on operating system.
                    %s
                '''

class EmbeddedConsoleExit(SystemExit):
    #   @FIXME
    #       Add docstring; what does this Error represent?
    pass


class EmptyStatement(Exception):
    #   @FIXME
    #       Add docstring; what does this Error represent?
    pass


class NotSettableError(Exception):
    '''
    This error should be raised when attempting to change
    any setting that isn't listed in `Cmd.settable`.
    '''
    pass


class PasteBufferError(EnvironmentError):
    #   @FIXME
    #       Add docstring; what does this Error represent?
    
    if sys.platform[:3] == 'win':
        errmsg = '''
                    Redirecting to or from paste buffer requires pywin32
                    to be installed on operating system.
                    
                    Download: 
                    http://sourceforge.net/projects/pywin32/
                '''
    elif sys.platform[:3] == 'dar':
        # Use built in pbcopy on Mac OSX
        pass
    else:
        errmsg = '''
                    Redirecting to or from paste buffer requires xclip 
                    to be installed on operating system.
                    
                    To install (Debian/Ubuntu):
                    
                    `sudo apt-get install xclip`
                '''
    def __init__(self):
        Exception.__init__(self, self.errmsg)
