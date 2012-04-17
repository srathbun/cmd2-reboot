# -*- coding: UTF-8 -*-
'''This file contains the state class and related code. It holds all of the settings for the current
   state of the cmd2 instance.'''
#   __future__ first
from    __future__  import  generators,         \
                            print_function,     \
                            with_statement


#   six: Python 2/3 Compatibility module
#   --------------------------------------------------------
#   `six` should (after `__future__`) get imported first,
#   because it deals with the different standard libraries
#   between Python 2 and 3.
import  six


#   Standard Library Imports
#   --------------------------------------------------------
import  os,         \
        platform,   \
        sys

import  cmd,        \
        copy,       \
        datetime,   \
        glob,       \
        optparse,   \
        re,         \
        subprocess, \
        tempfile,   \
        traceback

#   From:   http://packages.python.org/six/#module-six.moves
#
#   "NOTE: The urllib, urllib2, and urlparse modules have been combined 
#   in the urllib package in Python 3. 
#   
#   six.moves doesn’t not support their renaming because their 
#   members have been mixed across several modules in that package."
import  urllib

from    optparse    import  make_option
from    code        import (InteractiveConsole  ,  
                            InteractiveInterpreter)


#   Third Party Imports
#   --------------------------------------------------------
import  pyparsing


#   Cmd2 Modules
#   --------------------------------------------------------
from    .errors     import (EmbeddedConsoleExit ,
                            EmptyStatement      ,
                            NotSettableError    ,
                            PasteBufferError    ,
                            PASTEBUFF_ERR)

from    .parsers    import (ParsedString,
                            options     ,
                            options_defined)

from    .support    import (History,
                            Statekeeper,
                            stubbornDict,
                            cast,
                            can_clip,
                            get_paste_buffer,
                            replace_with_file_contents,
                            write_to_paste_buffer)

from    .input_parsers import (input_parser)

class state(object):
    '''The state class contains an intialized group of settings for a cmd2 instance.'''
    #       CURRENT IDEA (subject to change):
    #       Refactor into a Settings class, subdivided into:
    #       -   settable/not-settable
    #       -   input-related settings (parsing, case-sensitivity, shortcuts, etc.)
    #       -   output-related settings (printing time, prompt, etc.)
    #       -   component-level settings (history settings into history class, etc.)
    def __init__(self):
        self.echo                = False
        self.case_insensitive    = True      # Commands recognized regardless of case
        self.continuation_prompt = '> '
        self.timing              = False     # Prints elapsed time for each command

        #   @FIXME?
        #       Should this override cmd's `IDENTCHARS`?

        # make sure your terminators are not in legal_chars!
        self.legal_chars         = u'!#$%.:?@_' + pyparsing.alphanums + pyparsing.alphas8bit
        self.shortcuts           = { '?' : 'help' ,
                                '!' : 'shell',
                                '@' : 'load' ,
                                '@@': '_relative_load'}

        self.abbrev              = True          # Recognize abbreviated commands
        self.current_script_dir  = None
        self.debug               = True
        self.default_file_name   = 'command.txt' # For `save`, `load`, etc.
        self.default_to_shell    = False
        self.default_extension   = 'txt'         # For `save`, `load`, etc.
        self.hist_exclude        = {'ed','edit','eof','history','hi','l','li','list','run','r'}
        self.feedback_to_output  = False         # Do include nonessentials in >, | output
        self.kept_state          = None
        self.locals_in_py        = True
        self.no_special_parse    = {'ed','edit','exit','set'}
        self.quiet               = False         # Do not suppress nonessential output
        self.redirector          = '>'           # for sending output to file
        self.reserved_words      = []

        #   @FIXME
        #       Refactor into a Settings class (subdivided into settable/not-settable)
        self.settable            = stubbornDict(
            '''
            abbrev                Accept abbreviated commands
            case_insensitive      upper- and lower-case both OK
            colors                Colorized output (*nix only)
            continuation_prompt   On 2nd+ line of input
            debug                 Show full error stack on error
            default_file_name     for `save`, `load`, etc.
            echo                  Echo command issued into output
            editor                Program used by `edit`
            feedback_to_output    include nonessentials in `|`, `>` results
            prompt                Shell prompt
            quiet                 Don't print nonessential feedback
            timing                Report execution times
            ''')

        #   ************************************
        #   End "original" variable declarations
        #   ************************************
        #   Starting here, variables were collected
        #   together from various places within the class.

        self._STOP_AND_EXIT       = True # distinguish end of script file from actual exit
        self._STOP_SCRIPT_NO_EXIT = -999

        self.editor = os.environ.get('EDITOR')
        if not self.editor:
            if sys.platform[:3] == 'win':
                self.editor = 'notepad'
            else:
                for self.editor in {'gedit', 'kate', 'vim', 'emacs', 'nano', 'pico'}:
                    if subprocess.Popen(['which', self.editor], stdout=subprocess.PIPE).communicate()[0]:
                        break

        #   @FIXME
        #       Refactor into [config? output?] module
        self.colorcodes  =  {
                        # non-colors
                        'bold'    :   {True:'\x1b[1m', False:'\x1b[22m'},
                        'underline':  {True:'\x1b[4m', False:'\x1b[24m'},
                        # colors
                        'blue'    :   {True:'\x1b[34m',False:'\x1b[39m'},
                        'cyan'    :   {True:'\x1b[36m',False:'\x1b[39m'},
                        'green'   :   {True:'\x1b[32m',False:'\x1b[39m'},
                        'magenta' :   {True:'\x1b[35m',False:'\x1b[39m'},
                        'red'     :   {True:'\x1b[31m',False:'\x1b[39m'}
                       }

        self.colors = (platform.system() != 'Windows')

        #   @FIXME
        #       Refactor this settings block into 
        #       parsers.py
        self.allow_blank_lines   =   False
        self.comment_grammars    =   pyparsing.Or([  pyparsing.pythonStyleComment,
                                                pyparsing.cStyleComment ])
        self.comment_grammars.addParseAction(lambda x: '')
        self.comment_in_progress =   '/*' + pyparsing.SkipTo(pyparsing.stringEnd ^ '*/')
        self.multiline_commands  =   []
        self.prefix_parser       =   pyparsing.Empty()
        self.terminators         =   [';']

        self.input_parser = input_parser(self)

#    @FIXME
#    commented out in Cmd, Purpose?
#         self.settings_from_cmd = frozenset({
#                                     'doc_header',
#                                     'doc_leader',
#                                     'identchars',
#                                     'intro',
#                                     'lastcmd',
#                                     'misc_header',
#                                     'nohelp',
#                                     'prompt',
#                                     'ruler',
#                                     'undoc_header',
#                                     'use_rawinput'})

#         self.settings_from_cmd2 = ( 'abbrev',
#                                     'case_insensitive',
#                                     'continuation_prompt',
#                                     'current_script_dir',
#                                     'debug',
#                                     'default_file_name',
#                                     'default_to_shell',
#                                     'default_extension',
#                                     'echo',
#                                     'hist_exclude',
#                                     'feedback_to_output',
#                                     'kept_state',
#                                     'legal_chars',
#                                     'locals_in_py',
#                                     'no_special_parse',
#                                     'quiet',
#                                     'redirector',
#                                     'reserved_words',
#                                     'shortcuts',
#                                     'timing')

#         self.settings_for_parsing = ('abbrev',
#                                      'case_insensitive',
#                                      'default_to_shell',
#                                      'legal_chars',
#                                      'locals_in_py',
#                                      'no_special_parse',
#                                      'redirector',
#                                      'reserved_words',
#                                      'shortcuts')
