# -*- coding: UTF-8 -*-
'''The Cmd class in this module is the core of the cmd2 package.'''
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




#   Metadata
#   --------------------------------------------------------
__version__     = '0.6.5'
__copyright__   = '?'   #@FIXME
__license__     = '?'   #@FIXME
__status__      = '?'   #@FIXME

__author__      = 'Catherine Devlin'
__email__       = '?'   #@FIXME
__maintainer__  = '?'   #@FIXME
__credits__     = '?'   #@FIXME





if six.PY3:
    # 
    # Packrat is causing Python3 errors that I don't understand.
    # 
    #     > /usr/local/Cellar/python3/3.2/lib/python3.2/site-packages/pyparsing-1.5.6-py3.2.egg/pyparsing.py(999)scanString()
    #     -> nextLoc,tokens = parseFn( instring, preloc, callPreParse=False )
    #     (Pdb) n
    #     NameError: global name 'exc' is not defined
    #     
    #     (Pdb) parseFn
    #     <bound method Or._parseCache of {Python style comment ^ C style comment}>
    # 
    # (2011-07-28) Bug report filed: 
    #     https://sourceforge.net/tracker/?func=detail&atid=617311&aid=3381439&group_id=97203
    # 
    pyparsing.ParserElement.enablePackrat()



#   @FIXME
#       Consider:
#       *   refactoring into the Cmd class
#       *   using `__getattr__()` instead
def _attr_get_(obj, attr):
    '''
    Returns an attribute's value (or `None` if undefined; no error).
    Analagous to `.get()` for dictionaries.  
    
    Useful when checking for the value of options that may not have 
    been defined on a given method.
    '''
    try:
        return getattr(obj, attr)
    except AttributeError:
        return None

optparse.Values.get = _attr_get_    #   this is the only use of _attr_get_()



#   @FIXME
#       Move to parsers module...without breaking
#       any code in this file
pyparsing.ParserElement.setDefaultWhitespaceChars(' \t')



class Cmd(cmd.Cmd):
    #   @FIXME
    #       Add DocString 
    #       (This *is* the core class, after all!)
    
    
    #   @FIXME
    #       Refactor into a Settings class, subdivided into:
    #       -   settable/not-settable
    #       -   input-related settings (parsing, case-sensitivity, shortcuts, etc.)
    #       -   output-related settings (printing time, prompt, etc.)
    #       -   component-level settings (history settings into history class, etc.)
    echo                = False
    case_insensitive    = True      # Commands recognized regardless of case
    continuation_prompt = '> '  
    timing              = False     # Prints elapsed time for each command
    
    # make sure your terminators are not in legal_chars!
    legal_chars         = u'!#$%.:?@_' + pyparsing.alphanums + pyparsing.alphas8bit
    shortcuts           = { '?' : 'help' , 
                            '!' : 'shell', 
                            '@' : 'load' , 
                            '@@': '_relative_load'}

    abbrev              = True          # Abbreviated commands recognized
    current_script_dir  = None
    debug               = False
    default_file_name   = 'command.txt' # For `save`, `load`, etc.
    default_to_shell    = False
    default_extension   = 'txt'         # For `save`, `load`, etc.
    hist_exclude        = 'run r list l history hi ed edit li eof'.split()
    feedback_to_output  = False         # Do include nonessentials in >, | output
    kept_state          = None
    locals_in_py        = True
    no_special_parse    = 'set ed edit exit'.split()
    quiet               = False         # Do not suppress nonessential output
    redirector          = '>'           # for sending output to file
    reserved_words      = []
    
    #   @FIXME
    #       Refactor into a Settings class (subdivided into settable/not-settable)
    settable            = stubbornDict(
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
        prompt                
        quiet                 Don't print nonessential feedback
        timing                Report execution times
        ''')
    
    #   ************************************
    #   End "original" variable declarations
    #   ************************************
    #   Starting here, variables were collected
    #   together from various places within the class.
    
    _STOP_AND_EXIT       = True # distinguish end of script file from actual exit
    _STOP_SCRIPT_NO_EXIT = -999
    
    editor = os.environ.get('EDITOR')
    if not editor:
        if sys.platform[:3] == 'win':
            editor = 'notepad'
        else:
            for editor in ['gedit', 'kate', 'vim', 'emacs', 'nano', 'pico']:
                if subprocess.Popen(['which', editor], stdout=subprocess.PIPE).communicate()[0]:
                    break
    
    #   @FIXME
    #       Refactor into [config? output?] module
    colorcodes =  {
                  'bold'    :   {True:'\x1b[1m', False:'\x1b[22m'},
                  'underline':  {True:'\x1b[4m', False:'\x1b[24m'},
                  
                  'blue'    :   {True:'\x1b[34m',False:'\x1b[39m'},
                  'cyan'    :   {True:'\x1b[36m',False:'\x1b[39m'},
                  'green'   :   {True:'\x1b[32m',False:'\x1b[39m'},
                  'magenta' :   {True:'\x1b[35m',False:'\x1b[39m'},
                  'red'     :   {True:'\x1b[31m',False:'\x1b[39m'}
                  }
    
    colors = (platform.system() != 'Windows')
    
    
    #   @FIXME
    #       Refactor this settings block into 
    #       parser module
    allow_blank_lines   =   False
    comment_grammars    =   pyparsing.Or([  pyparsing.pythonStyleComment, 
                                            pyparsing.cStyleComment ])
    comment_grammars.addParseAction(lambda x: '')
    comment_in_progress =   pyparsing.Literal('/*') + \
                            pyparsing.SkipTo(pyparsing.stringEnd ^ '*/')
    multiline_commands  =   []
    prefix_parser       =   pyparsing.Empty()
    terminators         =   [';']
    
    
    def __init__(self, *args, **kwargs):
        #   @FIXME
        #       Add DocString
        
        #   @FIXME
        #       Describe what happens in __init__
        
        #   @FIXME
        #       Is there a way to use `__super__`
        #       that is Python 2+3 compatible?
        cmd.Cmd.__init__(self, *args, **kwargs)
        
        self.initial_stdout = sys.stdout
        self.history        = History()
        self.pystate        = {}

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
        
        
        #   @FIXME
        #       Why does this need to have `reverse=True`?
        self.shortcuts      = sorted(self.shortcuts.items(), reverse=True)
        
        #   @FIXME
        #       Refactor into parsing module
        self._init_parser()
        
    
#     def __getattr__(self, name):
#         #   Only called when attr not found
#         #   in the usual places
#         #print("\n" + 'CALLING __getattr__({})'.format( name ) + "\n")
#         #return self.settings[name]
        
        
    
    #   @FIXME
    #       Refactor into parser module
    #   @FIXME
    #       Refactor into NOT a god-initializer 
    def _init_parser(self):
        #   @FIXME
        #       Add docstring
        
        #   @NOTE
        #   This is one of the biggest pain points of the existing code.
        #   To aid in readability, I CAPITALIZED all variables that are
        #   not set on `self`. 
        #
        #   That means that CAPITALIZED variables aren't
        #   used outside of this method.
        #
        #   Doing this has allowed me to more easily read what
        #   variables become a part of other variables during the
        #   building-up of the various parsers.
        #
        #   I realize the capitalized variables is unorthodox
        #   and potentially anti-convention.  But after reaching out
        #   to the project's creator several times over roughly 5
        #   months, I'm still working on this project alone...
        #   And without help, this is the only way I can move forward.
        #
        #   Of course, if the impossible happens and this code 
        #   gets cleaned up, then the variables will be restored to 
        #   proper capitalization.
        #
        #   —Zearin
        #   http://github.com/zearin
        #   2012 Mar 26
        
        #   Aliased for readability inside this method
        PYP = pyparsing
        
        #   Tell pyparsing how to parse 
        #   file input from '< filename'
        #   ----------------------------
        FILENAME    = PYP.Word(self.legal_chars + '/\\')
        INPUT_MARK  = PYP.Literal('<')
        INPUT_MARK.setParseAction(lambda x: '')
        INPUT_FROM  = FILENAME('INPUT_FROM')
        INPUT_FROM.setParseAction(replace_with_file_contents)
        
        
        DO_NOT_PARSE            =   self.comment_grammars       |   \
                                    self.comment_in_progress    |   \
                                    PYP.quotedString
                                    
        #OUTPUT_PARSER = (PYP.Literal('>>') | (PYP.WordStart() + '>') | PYP.Regex('[^=]>'))('output')
        OUTPUT_PARSER           =  (PYP.Literal(   2 * self.redirector) | \
                                   (PYP.WordStart()  + self.redirector) | \
                                    PYP.Regex('[^=]' + self.redirector))('output')

        PIPE                    =   PYP.Keyword('|', identChars='|')

        STRING_END              =   PYP.stringEnd ^ '\nEOF'
        
        TERMINATOR_PARSER       =   PYP.Or([
                                        (hasattr(t, 'parseString') and t)
                                        or PYP.Literal(t) for t in self.terminators
                                    ])('terminator')
        
        #   moved here from class-level variable
        self.URLRE              =   re.compile('(https?://[-\\w\\./]+)')
        
        self.keywords           =   self.reserved_words + [fname[3:] for fname in dir(self) if fname.startswith('do_')]        
        
        self.comment_grammars.ignore(PYP.quotedString).setParseAction(lambda x: '')
        
        #   not to be confused with
        #   multiln_parser (below)
        self.multiline_command  =   PYP.Or([
                                        PYP.Keyword(c, caseless=self.case_insensitive) 
                                        for c in self.multiline_commands
                                    ])('multiline_command')
        
        #
        #   ONELN_COMMAND 
        #
        ONELN_COMMAND           =   (   ~self.multiline_command + 
                                        PYP.Word(self.legal_chars)
                                    )('command')
        
        #   CASE SENSITIVITY for 
        #   ONELN_COMMAND and self.multiline_command
        if self.case_insensitive:
            #   Set parsers to account for case insensitivity (if appropriate)
            self.multiline_command.setParseAction(lambda x: x[0].lower())
            ONELN_COMMAND.setParseAction(lambda x: x[0].lower())
                                    
        self.save_parser        = ( PYP.Optional(PYP.Word(PYP.nums)^'*')('idx')
                                  + PYP.Optional(PYP.Word(self.legal_chars + '/\\'))('fname') 
                                  + PYP.stringEnd)
        
        AFTER_ELEMENTS          =   PYP.Optional(PIPE + 
                                                    PYP.SkipTo(
                                                        OUTPUT_PARSER ^ STRING_END,
                                                        ignore=DO_NOT_PARSE
                                                    )('pipeTo')
                                                ) + \
                                    PYP.Optional(OUTPUT_PARSER + 
                                                 PYP.SkipTo(
                                                     STRING_END, 
                                                     ignore=DO_NOT_PARSE
                                                 ).setParseAction(lambda x: x[0].strip())('outputTo')
                                             )

        self.multiln_parser = (((self.multiline_command ^ ONELN_COMMAND) 
                                +   PYP.SkipTo(
                                        TERMINATOR_PARSER, 
                                        ignore=DO_NOT_PARSE
                                    ).setParseAction(lambda x: x[0].strip())('args') 
                                +   TERMINATOR_PARSER)('statement') 
                                +   PYP.SkipTo(
                                        OUTPUT_PARSER ^ PIPE ^ STRING_END, 
                                        ignore=DO_NOT_PARSE
                                    ).setParseAction(lambda x: x[0].strip())('suffix') 
                                + AFTER_ELEMENTS
                             )
        
        self.multiln_parser.ignore(self.comment_in_progress)
        
        self.singleln_parser  = (
                                    (   ONELN_COMMAND + PYP.SkipTo(
                                        TERMINATOR_PARSER 
                                        ^ STRING_END 
                                        ^ PIPE 
                                        ^ OUTPUT_PARSER, 
                                        ignore=DO_NOT_PARSE
                                    ).setParseAction(lambda x:x[0].strip())('args'))('statement')
                                + PYP.Optional(TERMINATOR_PARSER)
                                + AFTER_ELEMENTS)
        #self.multiln_parser  = self.multiln_parser.setResultsName('multiln_parser')
        #self.singleln_parser = self.singleln_parser.setResultsName('singleln_parser')
        
        
        #   Configure according to `allow_blank_lines` setting
        if self.allow_blank_lines:
            self.blankln_termination_parser = PYP.NoMatch
        else:
            self.blankln_terminator = (PYP.lineEnd + PYP.lineEnd)('terminator')
            self.blankln_terminator.setResultsName('terminator')
            self.blankln_termination_parser = (
                                                (self.multiline_command ^ ONELN_COMMAND) 
                                                + PYP.SkipTo(
                                                    self.blankln_terminator, 
                                                    ignore=DO_NOT_PARSE
                                                ).setParseAction(lambda x: x[0].strip())('args') 
                                                + self.blankln_terminator)('statement')

        self.blankln_termination_parser = self.blankln_termination_parser.setResultsName('statement')
        
        self.parser = self.prefix_parser + (STRING_END                      |
                                            self.multiln_parser             |
                                            self.singleln_parser            |
                                            self.blankln_termination_parser | 
                                            self.multiline_command          +  
                                            PYP.SkipTo(
                                                STRING_END, 
                                                ignore=DO_NOT_PARSE) 
                                            )
        
        self.parser.ignore(self.comment_grammars)
        
        # a not-entirely-satisfactory way of distinguishing
        # '<' as in "import from" from 
        # '<' as in "lesser than"
        self.input_parser = INPUT_MARK                + \
                            PYP.Optional(INPUT_FROM)  + \
                            PYP.Optional('>')         + \
                            PYP.Optional(FILENAME)    + \
                            (PYP.stringEnd | '|')
        
        self.input_parser.ignore(self.comment_in_progress)               
    
    def _cmdloop(self, intro=None):
        '''
        Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.
        '''

        # An almost perfect copy from Cmd; however, the pseudo_raw_input portion
        # has been split out so that it can be called separately
        
        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey+': complete')
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro) + "\n")
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    line = self.pseudo_raw_input(self.prompt)
                if (self.echo) and (isinstance(self.stdin, file)):
                    self.stdout.write(line + '\n')
                stop = self.onecmd_plus_hooks(line)
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline #   okay to *re-import* readline?
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass    
            return stop

    def _default(self, statement):
        '''
        Accepts a fully parsed `statement` and executes it.  Sends the 
        statement to the shell if `default_to_shell` is `True`.  
        '''
        arg = statement.full_parsed_statement()
        if self.default_to_shell:
            result = os.system(arg)
            if not result:
                return self.postparsing_postcmd(None)
        return self.postparsing_postcmd(self.default(arg))

    def poutput(self, msg):
        '''
        Shortcut for `self.stdout.write()`. (Adds newline if necessary.)
        '''
        if msg:
            self.stdout.write(msg)
            if msg[-1] is not '\n':
                self.stdout.write('\n')
    
    def perror(self, errmsg, statement=None):
        '''
        Prints `errmsg`.  Includes a traceback if `debug` is `True`.
        '''
        if self.debug:
            traceback.print_exc()
        print( str(errmsg) )
    
    def pfeedback(self, msg):
        '''
        For printing nonessential feedback.  Can be silenced with `quiet`.
        `feedback_to_output` controls whether to include in redirected output.
        '''
        if not self.quiet:
            if self.feedback_to_output:
                self.poutput(msg)
            else:
                print(msg)
    
    def colorize(self, val, color):
        '''
        Given a string (`val`), returns that string wrapped in UNIX-style 
        special characters that turn on (and then off) text color and style.
        If the `colors` environment variable is `False`, or the application
        is running on Windows, will return `val` unchanged.
        
        `color` should be one of the supported strings (or styles):
       
        red/blue/green/cyan/magenta, bold, underline
        '''
        if self.colors and (self.stdout == self.initial_stdout):
            return  self.colorcodes[color][True] + \
                    val                          + \
                    self.colorcodes[color][False]
        return val

    def preparse(self, raw, **kwargs):
        '''
        This is a hook for subclasses to process input before it gets parsed. It 
        does nothing by default.
        '''
        return raw
    
    def postparse(self, parse_result):
        '''
        This is a hook for subclasses to process input after it gets parsed. It 
        does nothing by default.
        '''
        return parse_result
   
    #   @FIXME
    #       Refactor into parser module
    def parsed(self, raw, **kwargs):
        #   @FIXME
        #       Add DocString
        if isinstance(raw, ParsedString):
            parsed_str = raw
        else:
            # preparse is an overridable hook; default makes no changes
            parsed_str = self.preparse(raw, **kwargs).lstrip()
            parsed_str = self.input_parser.transformString(parsed_str)
            parsed_str = self.comment_grammars.transformString(parsed_str)
            for (shortcut, expansion) in self.shortcuts:
                if parsed_str.lower().startswith(shortcut):
                    parsed_str = parsed_str.replace(shortcut, expansion + ' ', 1)
                    break
            result              = self.parser.parseString(parsed_str)
            result['raw']       = raw            
            result['command']   = result.multiline_command or result.command        
            result              = self.postparse(result)
            parsed_str               = ParsedString(result.args)
            parsed_str.parsed        = result
            parsed_str.parser        = self.parsed
        for (key, val) in kwargs:
            parsed_str.parsed[key] = val
        return parsed_str
              
    def postparsing_precmd(self, statement):
        '''
        This is a hook for subclasses to process parsed input before
        any command receives it.  
        
        It does nothing by default.
        '''
        stop = 0
        return stop, statement
    
    def postparsing_postcmd(self, stop):
        '''
        This is a hook for subclasses to process parsed input after a command
        has received it an finished execution.
        
        It does nothing by default.
        '''
        return stop
    
    def _func_named(self, arg):
        '''
        This method searches all `do_` methods for a match with `arg`.  It 
        returns the matched method.
        
        If no exact matches are found, it searches for shortened versions
        of command names (and keywords) for an unambiguous match.
        '''
        result = None
        target = 'do_' + arg
        if target in dir(self):
            result = target
        else:
            if self.abbrev:   # accept shortened versions of commands
                funcs = [fname for fname in self.keywords 
                                if fname.startswith(arg)]
                if len(funcs) is 1:
                    result = 'do_' + funcs[0]
        return result
    
    def onecmd(self, line):
        '''
        Interpret the argument as though it had been typed in response
        to the prompt.  (Overrides `cmd.onecmd()`.)

        This may be overridden, but shouldn't normally need to be.
        (See `precmd()` and `postcmd()` for useful execution hooks.)
        
        Returns a flag indicating whether interpretation of commands by 
        the interpreter should stop.
        '''
        statement    = self.parsed(line)
        self.lastcmd = statement.parsed.raw   
        funcname     = self._func_named(statement.parsed.command)
        if not funcname:
            return self._default(statement)
        try:
            func    = getattr(self, funcname)
        except AttributeError:
            return self._default(statement)
        stop = func(statement) 
        return stop                
        
    def onecmd_plus_hooks(self, line):
        '''
        Runs `onecmd()` with calls to hook methods at the appropriate places.
        '''
        # The outermost level of try/finally nesting can be condensed
        # once Python 2.4 support can be dropped.
        #-----------------------------------------------------------
        #   @FIXME
        #       Python 2.4 was released in 2004. 
        #       Think we can drop that outermost try/finally yet? :)
        stop = 0
        try:
            try:
                statement           = self.complete_statement(line)
                (stop, statement)   = self.postparsing_precmd(statement)
                if stop:
                    return self.postparsing_postcmd(stop)
                if statement.parsed.command not in self.hist_exclude:
                    self.history.append(statement.parsed.raw)      
                try:
                    self.redirect_output(statement)
                    timestart   = datetime.datetime.now()
                    statement   = self.precmd(statement)
                    stop        = self.postcmd(
                                    self.onecmd(statement), 
                                    statement)
                    if self.timing:
                        self.pfeedback('Elapsed: %s' % 
                                        str(datetime.datetime.now() - timestart))
                finally:
                    self.restore_output(statement)
            except EmptyStatement:
                return 0
            except Exception, err:
                self.perror(str(err), statement)
        finally:
            return self.postparsing_postcmd(stop)        
    
    def complete_statement(self, line):
        '''
        Keep accepting lines of input until the command is complete.
        '''
        #   @FIXME
        #       Describe: How is this different from `Cmd.complete_statement()`?
        
        if (not line) or (
            not pyparsing.Or(self.comment_grammars).
                setParseAction(lambda x: '').transformString(line)):
            raise EmptyStatement
        statement = self.parsed(line)
        while statement.parsed.multiline_command and \
             (statement.parsed.terminator == ''):
            statement = '%s\n%s' % (statement.parsed.raw, 
                                    self.pseudo_raw_input(self.continuation_prompt))                
            statement = self.parsed(statement)
        if not statement.parsed.command:
            raise EmptyStatement
        return statement
    
    def redirect_output(self, statement):
        #   @FIXME
        #       Add DocString
        if statement.parsed.pipeTo:
            self.kept_state = Statekeeper(self, ('stdout',))
            self.kept_sys   = Statekeeper(sys,  ('stdout',))
            self.redirect   = subprocess.Popen( statement.parsed.pipeTo, 
                                                shell   =True, 
                                                stdout  =subprocess.PIPE, 
                                                stdin   =subprocess.PIPE)
            sys.stdout      = self.stdout = self.redirect.stdin
        elif statement.parsed.output:
            if (not statement.parsed.outputTo) and (not can_clip):
                raise EnvironmentError('Cannot redirect to paste buffer; install `xclip` and re-run to enable.')
            self.kept_state = Statekeeper(self, ('stdout',))            
            self.kept_sys   = Statekeeper(sys, ('stdout',))
            if statement.parsed.outputTo:
                mode = 'w'
                if statement.parsed.output is 2 * self.redirector:
                    mode = 'a'
                sys.stdout = self.stdout = open(os.path.expanduser(statement.parsed.outputTo), 
                                                mode)                            
            else:
                sys.stdout = self.stdout = tempfile.TemporaryFile(mode="w+")
                if statement.parsed.output == '>>':
                    self.stdout.write(get_paste_buffer())
                    
    def restore_output(self, statement):
        #   @FIXME
        #       Add DocString
        if self.kept_state:
            if statement.parsed.output:
                if not statement.parsed.outputTo:
                    self.stdout.seek(0)
                    write_to_paste_buffer(self.stdout.read())
            elif statement.parsed.pipeTo:
                for result in self.redirect.communicate():              
                    self.kept_state.stdout.write(result or '')                        
            self.stdout.close()
            self.kept_state.restore()  
            self.kept_sys.restore()
            self.kept_state = None                        
                        
    def read_file_or_url(self, fname):
        '''
        Opens `fname` as a file.  Accounts for user tilde expansion and URLs.
        '''
        #   @FIXME
        #       TODO: not working on localhost
        
        #   @FIXME
        #       Rewrite for readability and less
        #       indent-hell
        if isinstance(fname, file):
            result = open(fname, 'r')
        else:
            match   = self.urlre.match(fname)
            if match:
                result  = urllib.urlopen(match.group(1))
            else:
                fname   = os.path.expanduser(fname)
                try:
                    result  = open( os.path.expanduser(fname), 'r')
                except IOError:                    
                    result  = open('%s.%s' % (os.path.expanduser(fname), 
                                              self.default_extension), 
                                    'r')
        return result
        
    def pseudo_raw_input(self, prompt):
        '''
        Extracted from `cmd.cmdloop()`. Similar to `raw_input()`, but 
        accounts for changed stdin/stdout.
        '''
        
        if self.use_rawinput:
            try:
                line = raw_input(prompt)
            except EOFError:
                line = 'EOF'
        else:
            self.stdout.write(prompt)
            self.stdout.flush()
            line = self.stdin.readline()
            if not len(line):
                line = 'EOF'
            else:
                if line[-1] == '\n': # this was always true in Cmd
                    line = line[:-1] 
        return line
    
    def select(self, choices, prompt='Your choice? '):
        '''
        Presents a numbered menu to the user.  Returns the item chosen.
        (Modeled after the bash shell's `SELECT`.)
           
           Argument `choices` can be:

             | a single string      -> split into one-word choices
             | a list of strings    -> will be offered as choices
             | a list of tuples     -> interpreted as (value, text), so 
                                       that the return value can differ from
                                       the text advertised to the user
        '''
        if isinstance(choices, six.string_types):
            choices = zip(choices.split(), choices.split())
        fullchoices = []
        for item in choices:
            if isinstance(item, six.string_types):
                fullchoices.append((item, item))
            else:
                try:
                    fullchoices.append((item[0], item[1]))
                except IndexError:
                    fullchoices.append((item[0], item[0]))
        for (index, (value, text)) in enumerate(fullchoices):
            #   @FIXME
            #       Unused variable `value`
            self.poutput('  %2d. %s\n' % (index+1, text))
        while True:
            response    = raw_input(prompt)
            try:
                response    = int(response)
                result      = fullchoices[response - 1][0]
                break
            except ValueError:
                pass # loop and ask again
        return result
    
    def last_matching(self, arg):
        '''
        Gets the most recent history match for `arg`.
        '''
        
        #   @FIXME
        #       Consider refactoring into 
        #       `History` class (in `support` module)
        try:
            if arg:
                return self.history.get(arg)[-1]
            else:
                return self.history[-1]
        except IndexError:
            return None        
    
    def fileimport(self, statement, source):
        '''
        Reads `source` from a file and returns its contents.
        '''
        
        #   @FIXME
        #       Unused argument: `statement`
        try:
            fyle = open(os.path.expanduser(source))
        except IOError:
            #   @FIXME
            #       Why doesn't this use `self.poutput()` or `self.perror()`?
            self.stdout.write("Couldn't read from file %s\n" % source)
            return ''
        data = fyle.read()
        fyle.close()
        return data

    def run_commands_at_invocation(self, callargs):
        '''
        Runs commands in `omecmd_plus_hooks` before executing callargs.
        '''
        for initial_command in callargs:
            if self.onecmd_plus_hooks(initial_command + '\n'):
                return self._STOP_AND_EXIT

    def cmdloop(self):
        '''
        Initializes a parser and runs `_cmdloop()`.
        '''
        
        #   @FIXME
        #       Why isn't this using cmd2's own OptionParser?
        parser = optparse.OptionParser()
        parser.add_option(  '-t', 
                            '--test', 
                            dest    ='test',
                            action  ='store_true', 
                            help    ='Test against transcript(s) in FILE (accepts wildcards)')
        (callopts, callargs) = parser.parse_args()
        
        #if callopts.test:
        #    self.runTranscriptTests(callargs)
        #else:
        #    if not self.run_commands_at_invocation(callargs):
        #        self._cmdloop() 
        
        if not self.run_commands_at_invocation(callargs):
            self._cmdloop() 
         
         
    #-----------------------------------------------------
    #   COMMANDS
    #   ========
    #   Only `do_*` commands from here to the end
    #   of the class.
    #-----------------------------------------------------
    def do_cmdenvironment(self, args):
        '''
        Summary report of interactive parameters.
        '''
        env_string  =   \
            '''\nCommands:
            are %(casesensitive)s case-sensitive
            may be terminated with: %(terminators)s
            \nSettable parameters: %(settable)s'''.lstrip()
        
        self.poutput( env_string.lstrip() % {
                'casesensitive' : (self.case_insensitive and 'NOT') or '',
                'terminators'   : str(self.terminators),
                'settable'      : '\n\t' + '\n\t'.join(sorted(self.settable))
            })
        
    def do_help(self, arg):
        '''
        Prints help for the command `arg`.
        
        If no match for `arg` is found, falls back onto `do_help()` from 
        `cmd` in the standard lib.
        '''
        #   @FIXME
        #       Add DocString 
        #       (How is this different from `cmd.do_help()`?)
        if arg:
            funcname = self._func_named(arg)
            if funcname:
                func  = getattr(self, funcname)
                try:
                    func.optionParser.print_help(file=self.stdout)
                except AttributeError:
                    cmd.Cmd.do_help(self, funcname[3:])
        else:
            cmd.Cmd.do_help(self, arg)
        
    def do_shortcuts(self, args):
        '''
        Lists single-key shortcuts available.
        '''
        #   @FIXME
        #       Unused argument: `arg`
        result = "\n".join('%s: %s' % 
                            (sc[0], sc[1]) for sc in sorted(self.shortcuts)
                        )
        self.poutput("Single-key shortcuts for other commands:\n%s\n" % (result))

    def do_EOF(self, arg):
        #   @FIXME
        #       Add DocString
        #       
        #       *   should this always/never be called under 
        #           certain circumstances?
        #       *   error codes? (e.g., "return 0 on success, >0 on error")
        #       *   signals? (SIGINT, SIGHUP, SIGEOF, etc.)
        #
        
        #   @FIXME
        #       Unused argument: `arg`
        
        return self._STOP_SCRIPT_NO_EXIT # End of script; should not exit app
    
    do_eof  = do_EOF

    def do_quit(self, arg):
        '''
        Exits the currently-running `Cmd` shell.
        '''
        #   @FIXME
        #       Improve Docstring
        #       *   should this always/never be called under 
        #           certain circumstances?
        #       *   error codes? (e.g., "return 0 on success, >0 on error")
        #       *   signals? (SIGINT, SIGHUP, SIGEOF, etc.)
        return self._STOP_AND_EXIT
    
    do_exit = do_quit
    do_q    = do_quit

    @options([make_option(
                '-l',   '--long', 
                action  =   'store_true',
                help    =   'describe function of parameter')])
    def do_show(self, arg, opts):
        '''
        Shows value of a parameter.
        '''
        
        param   = arg.strip().lower()
        result  = {}
        maxlen  = 0
        for item in self.settable:
            if (not param) or item.startswith(param):
                result[item]   = '%s: %s' % (item, str(getattr(self, item)))
                maxlen      = max(maxlen, len(result[item]))
        if result:
            for item in sorted(result):
                if opts.long:
                    self.poutput('%s # %s' % (result[item].ljust(maxlen), self.settable[item]))
                else:
                    self.poutput(result[item])
        else:
            raise NotImplementedError("Parameter '%s' not supported (type 'show' for list of parameters)." % param)
    
    def do_set(self, arg):
        '''
        Sets a `cmd2` parameter.  Accepts abbreviated parameter names so long
        as there's no ambiguity.  Call without arguments to list settable 
        parameters and their values.
        '''
        try:
            
            statement,  \
            param_name, \
            val         = arg.parsed.raw.split(None, 2)
            val         = val.strip()
            param_name  = param_name.strip().lower()
            if param_name not in self.settable:
                hits =  [p for p in self.settable 
                            if p.startswith(param_name)]
                if len(hits) is 1:
                    param_name = hits[0]
                else:
                    return self.do_show(param_name)
            current_val = getattr(self, param_name)
            if (val[0] == val[-1]) and val[0] in ("'", '"'):
                val = val[1:-1]
            else:                
                val = cast(current_val, val)
            setattr(self, param_name, val)
            self.stdout.write('%s - was: %s\nnow: %s\n' % 
                                (param_name, 
                                current_val, 
                                val)
                            )
            if current_val != val:
                try:
                    onchange_hook = getattr(self, '_onchange_%s' % param_name)
                    onchange_hook(old=current_val, new=val)
                except AttributeError:
                    pass
        except (ValueError, AttributeError, NotSettableError):#, err:
            self.do_show( arg )
                
    def do_pause(self, arg):
        '''
        Displays the specified text, then waits for user to press RETURN.
        '''
        raw_input(arg + '\n')
        
    def do_shell(self, arg):
        '''
        Execute command as if at the OS prompt.
        '''
        os.system(arg)
                
    def do_py(self, arg):  
        '''
        py <command>: Executes a Python command.
        py: Enters interactive Python mode.
        
        End with:
            `Ctrl-D` (Unix) 
            `Ctrl-Z` (Windows)
            `quit()`
            `exit()`
        
        Non-python commands can be issued with `cmd('your command')`.
        
        Run python code from external files with `run('filename.py')`.
        '''
        self.pystate['self'] = self
        arg         = arg.parsed.raw[2:].strip()
        localvars   = (self.locals_in_py and self.pystate) or {}
        interp      = InteractiveConsole(locals = localvars)
        interp.runcode('import sys, os;sys.path.insert(0, os.getcwd())')
        if arg.strip():
            interp.runcode(arg)
        else:
            def quit():
                #   @FIXME: Add Docstring
                raise EmbeddedConsoleExit
            def onecmd_plus_hooks(arg):
                #   @FIXME: Add Docstring
                return self.onecmd_plus_hooks(arg + '\n')
            def run(arg):
                #   @FIXME: Add Docstring
                try:
                    fyle = open(arg)
                    interp.runcode(fyle.read())
                    fyle.close()
                except IOError, err:
                    self.perror(err)
            self.pystate['quit']    = quit
            self.pystate['exit']    = quit
            self.pystate['cmd']     = onecmd_plus_hooks
            self.pystate['run']     = run
            try:
                cprt        = 'Type "help", "copyright", "credits", or "license" for more information.'        
                keepstate   = Statekeeper(sys, ('stdin','stdout'))
                sys.stdout  = self.stdout
                sys.stdin   = self.stdin
                interp.interact(
                    banner  = "Python %s on %s\n%s\n(%s)\n%s" % (
                        sys.version, 
                        sys.platform, 
                        cprt, 
                        self.__class__.__name__, 
                        self.do_py.__doc__)
                    )
            except EmbeddedConsoleExit:
                pass
            keepstate.restore()
            
    @options([make_option(
                '-s', '--script', 
                action  =   "store_true", 
                help    =   "Script format; no separation lines"),
            ], 
            arg_desc    = '(limit on which commands to include)')
    def do_history(self, arg, opts):
        '''
        history [arg]: list past commands issued
        
        | no arg:         list all
        | arg is integer: list one history item, by index
        | arg is string:  string search
        | arg is /enclosed in forward-slashes/: regular expression search
        '''
        if arg:
            history = self.history.get(arg)
        else:
            history = self.history
        for hist_item in history:
            if opts.script:
                self.poutput(hist_item)
            else:
                self.stdout.write(hist_item.print_())
    
    def do_list(self, arg):
        '''
        list [arg]: List last command issued
        
        no arg                      -> list most recent command
        arg is integer              -> list one history item, by index
        a..b, a:b, a:, ..b          -> list spans from a (or start) to b (or end)
        arg is string               -> list all commands matching string search
        /arg in forward-slashes/    -> regular expression search
        '''
        try:
            history = self.history.span(arg or '-1')
        except IndexError:
            history = self.history.search(arg)
        for hist_item in history:
            self.poutput(hist_item.print_())

    do_hi   = do_history
    do_l    = do_list
    do_li   = do_list
        
    def do_ed(self, arg):
        '''
        ed:             edit most recent command in text editor
        ed [N]:         edit numbered command from history
        ed [filename]:  edit specified file name
        
        Commands are run after the editor is closed.
        
        To set which editor to use, either: 
            (1) `set edit [program-name]` or 
            (2) set the `EDITOR` environment variable
        '''
        
        if not self.editor:
            raise EnvironmentError("Please use 'set editor' to specify your text editing program of choice.")
        filename    = self.default_file_name
        if arg:
            try:
                buffer      = self.last_matching(int(arg))
            except ValueError:
                filename    = arg
                buffer      = ''
        else:
            buffer  = self.history[-1]

        if buffer:
            fyle = open(os.path.expanduser(filename), 'w')
            fyle.write(buffer or '')
            fyle.close()        
                
        os.system('%s %s' % (self.editor, filename))
        self.do__load(filename)
    
    do_edit = do_ed
                  
    def do_save(self, arg):
        '''
        `save [N] [filename.ext]`

        Saves command from history to file.

        | N => Number of command (from history), or `*`; 
        |      most recent command if omitted
        '''

        try:
            args = self.save_parser.parseString(arg)
        except pyparsing.ParseException:
            self.perror('Could not understand save target %s' % arg)
            raise SyntaxError(self.do_save.__doc__)
        fname = args.fname or self.default_file_name
        if args.idx == '*':
            save_me = '\n\n'.join(self.history[:])
        elif args.idx:
            save_me = self.history[int(args.idx)-1]
        else:
            save_me = self.history[-1]
        try:
            file = open(os.path.expanduser(fname), 'w')
            file.write(save_me)
            file.close()
            self.pfeedback('Saved to %s'  % (fname))
        except Exception, err:
            self.perror('Error saving %s' % (fname))
            self.perror(err)
            raise
            
    def do__relative_load(self, arg=None):
        '''
        Runs commands in script at file or URL. If called from within an
        already-running script, the filename will be interpreted relative to 
        that script's directory.
        '''
        if arg:
            arg             = arg.split(None, 1)
            targetname      = arg[0]
            args            = (arg[1:] or [''])[0]
            targetname      = os.path.join(
                                self.current_script_dir or '', 
                                targetname)
            self.do__load('%s %s' % (targetname, args))
    
    def do_load(self, arg=None):           
        '''
        Runs script of command(s) from a file or URL.
        '''
        if arg is None:
            targetname  = self.default_file_name
        else:
            arg         = arg.split(None, 1)
            targetname  = arg[0]
            
            #   @FIXME
            #       Unused variable: `arts`
            arts        = (arg[1:] or [''])[0].strip()
        try:
            target = self.read_file_or_url(targetname)
        except IOError, err:
            self.perror('Problem accessing script from %s: \n%s' % (targetname, err))
            return
        keepstate = Statekeeper(self,  ('stdin',
                                        'use_rawinput',
                                        'prompt',
                                        'continuation_prompt',
                                        'current_script_dir'))
        self.stdin              = target    
        self.use_rawinput       = False
        self.prompt             = self.continuation_prompt = ''
        self.current_script_dir = os.path.split(targetname)[0]
        stop                    = self._cmdloop()
        self.stdin.close()
        keepstate.restore()
        self.lastcmd            = ''
        return stop and (stop != self._STOP_SCRIPT_NO_EXIT)    
    
    do__load = do_load  # avoid an unfortunate legacy use of do_load from sqlpython
    
    def do_run(self, arg):
        '''
        run [arg]: re-runs an earlier command
        run [N]: runs the SQL that was run N commands ago
        
        no arg                      -> run most recent command
        arg is integer              -> run one history item, by index
        arg is string               -> run most recent command by string search
        /arg in forward-slashes/    -> run most recent by regex
        '''
        runme   = self.last_matching(arg)
        self.pfeedback(runme)
        if runme:
            stop    = self.onecmd_plus_hooks(runme)
    
    do_r    = do_run  


#   @FIXME
#       Since DocTests have been refactored into separate files,
#       and superceeded by PyVows for testing,
#       what might be a good purpose for this codeblock instead?
if __name__ == '__main__':
    doctest.testmod(optionflags = doctest.NORMALIZE_WHITESPACE)



'''
To make your application transcript-testable, replace 

::

    app = MyApp()
    app.cmdloop()
  
with

::

    app = MyApp()
    cmd2.run(app)
  
Then run a session of your application and paste the entire screen contents
into a file, `transcript.test`, and invoke the test like::

    python myapp.py --test transcript.test

Wildcards can be used to test against multiple transcript files.
'''