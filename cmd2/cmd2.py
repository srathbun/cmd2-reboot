# -*- coding: UTF-8 -*-
'''Variant on standard library's cmd with extra features.

To use, simply import cmd2.Cmd instead of cmd.Cmd; use precisely as though you
were using the standard library's cmd, while enjoying the extra features.

Searchable command history (commands: "hi", "li", "run")
Load commands from file, save to file, edit commands in file
Multi-line commands
Case-insensitive commands
Special-character shortcut commands (beyond cmd's "@" and "!")
Settable environment parameters
Optional _onchange_{paramname} called when environment parameter changes
Parsing commands with `optparse` options (flags)
Redirection to file with >, >>; input from file with <
Easy transcript-based testing of applications (see example/example.py)
Bash-style ``select`` available

Note that redirection with > and | will only work if `self.stdout.write()`
is used in place of `print`.  The standard library's `cmd` module is 
written to use `self.stdout.write()`, 

- Catherine Devlin, Jan 03 2008 - catherinedevlin.blogspot.com

mercurial repository at http://www.assembla.com/wiki/show/python-cmd2
'''
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


#   Standard Library Imports
#   --------------------------------------------------------
import  os,         \
        platform,   \
        sys

import  cmd

import  copy
import  datetime
import  glob
import  optparse
import  re
import  subprocess
import  tempfile
import  traceback

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
                            pastebufferr)

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
    '''
    Packrat is causing Python3 errors that I don't understand.
    
        > /usr/local/Cellar/python3/3.2/lib/python3.2/site-packages/pyparsing-1.5.6-py3.2.egg/pyparsing.py(999)scanString()
        -> nextLoc,tokens = parseFn( instring, preloc, callPreParse=False )
        (Pdb) n
        NameError: global name 'exc' is not defined
        
        (Pdb) parseFn
        <bound method Or._parseCache of {Python style comment ^ C style comment}>
    
    (2011-07-28) Bug report filed: 
        https://sourceforge.net/tracker/?func=detail&atid=617311&aid=3381439&group_id=97203
    '''
    pyparsing.ParserElement.enablePackrat()



#   @FIXME
#       Consider:
#       *   refactoring into the Cmd class
#       *   using `__getattr__()` instead
def _attr_get_(obj, attr):
    '''Returns an attribute's value (or None if undefined; no error).
       Analagous to `.get()` for dictionaries.  
       
       Useful when checking for the value of options that may not have 
       been defined on a given method.'''
    try:
        return getattr(obj, attr)
    except AttributeError:
        return None

optparse.Values.get = _attr_get_    #   this is the only use of _attr_get_()


#   @FIXME
#       Refactor into support module
if subprocess.mswindows:
    #   @FIXME
    #       Add DocString 
    #       (what does this roughly-100-line-codeblock do?)
    try:
        import win32clipboard
        def get_paste_buffer():
            win32clipboard.OpenClipboard(0)
            try:
                result = win32clipboard.GetClipboardData()
            except TypeError:
                result = ''  #non-text
            win32clipboard.CloseClipboard()
            return result            
        def write_to_paste_buffer(txt):
            win32clipboard.OpenClipboard(0)
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(txt)
            win32clipboard.CloseClipboard()        
    except ImportError:
        def get_paste_buffer(*args):
            raise OSError, pastebufferr % ('pywin32', 'Download from http://sourceforge.net/projects/pywin32/')
        write_to_paste_buffer = get_paste_buffer
elif sys.platform == 'darwin':
    can_clip = False
    try:
        # test for pbcopy - AFAIK, should always be installed on MacOS
        subprocess.check_call(  'pbcopy -help', 
                                shell   = True, 
                                stdout  = subprocess.PIPE, 
                                stdin   = subprocess.PIPE, 
                                stderr  = subprocess.PIPE)
        can_clip = True
    except (subprocess.CalledProcessError, OSError, IOError):
        pass
    if can_clip:
        def get_paste_buffer():
            pbcopyproc = subprocess.Popen(  'pbcopy -help', 
                                            shell   =True, 
                                            stdout  =subprocess.PIPE, 
                                            stdin   =subprocess.PIPE, 
                                            stderr  =subprocess.PIPE)
            return pbcopyproc.stdout.read()
        def write_to_paste_buffer(txt):
            pbcopyproc = subprocess.Popen(  'pbcopy', 
                                            shell   =True, 
                                            stdout  =subprocess.PIPE, 
                                            stdin   =subprocess.PIPE, 
                                            stderr  =subprocess.PIPE)
            pbcopyproc.communicate(txt.encode())
    else:
        def get_paste_buffer(*args):
            raise OSError, pastebufferr % ('pbcopy', 'Error should not occur on OS X; part of the default installation')
        write_to_paste_buffer = get_paste_buffer
else:
    can_clip = False
    try:
        subprocess.check_call(  'xclip -o -sel clip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE, 
                                            stderr  = subprocess.PIPE)
        can_clip = True
    except AttributeError:  # check_call not defined, Python < 2.5
        try:
            teststring  = 'Testing for presence of xclip.'
            xclipproc   = subprocess.Popen( 'xclip -sel clip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE)
            xclipproc.stdin.write(teststring)
            xclipproc.stdin.close()
            xclipproc   = subprocess.Popen( 'xclip -o -sel clip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE)        
            if xclipproc.stdout.read() == teststring:
                can_clip = True
        except Exception: # hate a bare Exception call, but exception classes vary too much b/t stdlib versions
            pass
    except Exception:
        pass # something went wrong with xclip and we cannot use it
    if can_clip:    
        def get_paste_buffer():
            xclipproc = subprocess.Popen(   'xclip -o -sel clip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE)
            return xclipproc.stdout.read()
        def write_to_paste_buffer(txt):
            xclipproc = subprocess.Popen(   'xclip -sel clip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE)
            xclipproc.stdin.write(txt.encode())
            xclipproc.stdin.close()
            # but we want it in both the "primary" and "mouse" clipboards
            xclipproc = subprocess.Popen(   'xclip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE)
            xclipproc.stdin.write(txt.encode())
            xclipproc.stdin.close()
    else:
        def get_paste_buffer(*args):
            raise OSError, pastebufferr % ('xclip', 'On Debian/Ubuntu, install with "sudo apt-get install xclip"')
        write_to_paste_buffer = get_paste_buffer


#   @FIXME
#       Move to parsers module...without breaking
#       any code in this file
pyparsing.ParserElement.setDefaultWhitespaceChars(' \t')



class Cmd(cmd.Cmd):
    #   @FIXME
    #       Add DocString 
    #       (This *is* the core class, after all!)
    
    
    #   @FIXME
    #       Refactor into a Settings class (subdivided into settable/not-settable)
    echo                = False
    case_insensitive    = True     # Commands recognized regardless of case
    continuation_prompt = '> '  
    timing              = False    # Prints elapsed time for each command
    
    # make sure your terminators are not in legalChars!
    legalChars          = u'!#$%.:?@_' + pyparsing.alphanums + pyparsing.alphas8bit
    shortcuts           = { '?' : 'help' , 
                            '!' : 'shell', 
                            '@' : 'load' , 
                            '@@': '_relative_load'}
                            
    excludeFromHistory  = 'run r list l history hi ed edit li eof'.split()
    default_to_shell    = False
    noSpecialParse      = 'set ed edit exit'.split()
    defaultExtension    = 'txt'         # For ``save``, ``load``, etc.
    default_file_name   = 'command.txt' # For ``save``, ``load``, etc.
    abbrev              = True          # Abbreviated commands recognized
    current_script_dir  = None
    reserved_words      = []
    feedback_to_output  = False         # Do include nonessentials in >, | output
    quiet               = False         # Do not suppress nonessential output
    debug               = False
    locals_in_py        = True
    kept_state          = None
    redirector          = '>'           # for sending output to file
    
    #   @FIXME
    #       Refactor into a Settings class (subdivided into settable/not-settable)
    settable            = stubbornDict(
        '''
        prompt
        colors                Colorized output (*nix only)
        continuation_prompt   On 2nd+ line of input
        debug                 Show full error stack on error
        default_file_name     for ``save``, ``load``, etc.
        editor                Program used by ``edit`` 	
        case_insensitive      upper- and lower-case both OK
        feedback_to_output    include nonessentials in `|`, `>` results 
        quiet                 Don't print nonessential feedback
        echo                  Echo command issued into output
        timing                Report execution times
        abbrev                Accept abbreviated commands
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

    prefixParser        = pyparsing.Empty()
    commentGrammars     = pyparsing.Or([pyparsing.pythonStyleComment, 
                                        pyparsing.cStyleComment])
    commentGrammars.addParseAction(lambda x: '')
    commentInProgress   =   pyparsing.Literal('/*') + \
                            pyparsing.SkipTo(pyparsing.stringEnd ^ '*/')
    terminators         = [';']
    blankLinesAllowed   = False
    multilineCommands   = []
    
    colorcodes =  {
                  'bold'    :   {True:'\x1b[1m', False:'\x1b[22m'},
                  'cyan'    :   {True:'\x1b[36m',False:'\x1b[39m'},
                  'blue'    :   {True:'\x1b[34m',False:'\x1b[39m'},
                  'red'     :   {True:'\x1b[31m',False:'\x1b[39m'},
                  'magenta' :   {True:'\x1b[35m',False:'\x1b[39m'},
                  'green'   :   {True:'\x1b[32m',False:'\x1b[39m'},
                  'underline':  {True:'\x1b[4m', False:'\x1b[24m'}
                  }
    
    colors = (platform.system() != 'Windows')
    
    
    #   @FIXME
    #       Refactor this settings block into 
    #       parser module
    prefixParser        = pyparsing.Empty()
    commentGrammars     = pyparsing.Or([pyparsing.pythonStyleComment, 
                                        pyparsing.cStyleComment])
    commentGrammars.addParseAction(lambda x: '')
    commentInProgress   =   pyparsing.Literal('/*') + \
                            pyparsing.SkipTo(pyparsing.stringEnd ^ '*/')
    terminators         = [';']
    blankLinesAllowed   = False
    multilineCommands   = []
    
    
    def __init__(self, *args, **kwargs):
        #   @FIXME
        #       Add DocString
        #   @FIXME
        #       Describe what happens in __init__
        cmd.Cmd.__init__(self, *args, **kwargs)
        self.initial_stdout = sys.stdout
        self.history        = History()
        self.pystate        = {}
        
        self.shortcuts      = sorted(self.shortcuts.items(), reverse=True)
        self.keywords       = self.reserved_words   + \
                                [fname[3:]  for fname in dir(self) 
                                 if fname.startswith('do_')]
                                 
        self.saveparser = ( pyparsing.Optional(pyparsing.Word(pyparsing.nums)^'*')("idx")     + 
                            pyparsing.Optional(pyparsing.Word(self.settings['legalChars'] + '/\\'))("fname")   +
                            pyparsing.stringEnd)
        
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
#         
#         self.settings_from_cmd2 = ( 'abbrev',
#                                     'case_insensitive',
#                                     'continuation_prompt',
#                                     'current_script_dir',
#                                     'debug',
#                                     'default_file_name',
#                                     'default_to_shell',
#                                     'defaultExtension',
#                                     'echo',
#                                     'excludeFromHistory',
#                                     'feedback_to_output',
#                                     'kept_state',
#                                     'legalChars',
#                                     'locals_in_py',
#                                     'noSpecialParse',
#                                     'quiet',
#                                     'redirector',
#                                     'reserved_words',
#                                     'shortcuts',
#                                     'timing')
# 
#         self.settings_for_parsing = ('abbrev',
#                                      'case_insensitive',
#                                      'default_to_shell',
#                                      'legalChars',
#                                      'locals_in_py',
#                                      'noSpecialParse',
#                                      'redirector',
#                                      'reserved_words',
#                                      'shortcuts')
                                     
        self.settings       = Settings()
        self.settings.settable.union(
            ' '.split('abbrev case_insensitive colors continuation_prompt debug default_file_name echo editor feedback_to_output prompt quiet timing')
            )
        

        self._init_parser()
        
    
    def __getattr__(self, name):
        #   Only called when attr not found
        #   in the usual places
        #print("\n" + 'CALLING __getattr__({})'.format( name ) + "\n")
        return self.settings[name]
        
    
    #   @FIXME
    #       Refactor into parser module
    def _init_parser(self):
        #   @FIXME
        #       Add docstring
        
        terminatorParser        = pyparsing.Or([(hasattr(t, 'parseString') and t) or pyparsing.Literal(t) for t in self.terminators])('terminator')
        stringEnd               = pyparsing.stringEnd ^ '\nEOF'
        self.multilineCommand   = pyparsing.Or([pyparsing.Keyword(c, caseless=self.case_insensitive) for c in self.multilineCommands])('multilineCommand')
        oneLineCommand          = (~self.multilineCommand + pyparsing.Word(self.legalChars))('command')
        pipe                    = pyparsing.Keyword('|', identChars='|')
        self.commentGrammars.ignore(pyparsing.quotedString).setParseAction(lambda x: '')
        doNotParse              = self.commentGrammars | self.commentInProgress | pyparsing.quotedString
        
        #   moved here from class-level variable
        self.urlre = re.compile('(https?://[-\\w\\./]+)')
        
        #outputParser = (pyparsing.Literal('>>') | (pyparsing.WordStart() + '>') | pyparsing.Regex('[^=]>'))('output')
        outputParser = (pyparsing.Literal(   2 * self.redirector) | \
                       (pyparsing.WordStart()  + self.redirector) | \
                        pyparsing.Regex('[^=]' + self.redirector))('output')

        
        
        afterElements           = pyparsing.Optional( pipe + 
                                                        pyparsing.SkipTo(
                                                            outputParser ^ stringEnd,       \
                                                            ignore=doNotParse)('pipeTo')) + \
                                                        pyparsing.Optional(
                                                            outputParser + 
                                                            pyparsing.SkipTo(
                                                                stringEnd, 
                                                                ignore=doNotParse
                                                            ).setParseAction(lambda x: x[0].strip())('outputTo')
                                                        )
        
        if self.case_insensitive:
            self.multilineCommand.setParseAction(lambda x: x[0].lower())
            oneLineCommand.setParseAction(lambda x: x[0].lower())
        if self.blankLinesAllowed:
            self.blankLineTerminationParser = pyparsing.NoMatch
        else:
            self.blankLineTerminator = (pyparsing.lineEnd + pyparsing.lineEnd)('terminator')
            self.blankLineTerminator.setResultsName('terminator')
            self.blankLineTerminationParser = ((self.multilineCommand ^ oneLineCommand) + pyparsing.SkipTo(self.blankLineTerminator, ignore=doNotParse).setParseAction(lambda x: x[0].strip())('args') + self.blankLineTerminator)('statement')
        self.multilineParser = (((self.multilineCommand ^ oneLineCommand) + pyparsing.SkipTo(terminatorParser, ignore=doNotParse).setParseAction(lambda x: x[0].strip())('args') + terminatorParser)('statement') + \
                                pyparsing.SkipTo(outputParser ^ pipe ^ stringEnd, ignore=doNotParse).setParseAction(lambda x: x[0].strip())('suffix') + afterElements)
        self.multilineParser.ignore(self.commentInProgress)
        self.singleLineParser = ((oneLineCommand + pyparsing.SkipTo(terminatorParser ^ stringEnd ^ pipe ^ outputParser, ignore=doNotParse).setParseAction(lambda x:x[0].strip())('args'))('statement') + \
                                 pyparsing.Optional(terminatorParser) + afterElements)
        #self.multilineParser  = self.multilineParser.setResultsName('multilineParser')
        #self.singleLineParser = self.singleLineParser.setResultsName('singleLineParser')
        self.blankLineTerminationParser = self.blankLineTerminationParser.setResultsName('statement')
        self.parser = self.prefixParser + ( stringEnd                       |
                                            self.multilineParser            |
                                            self.singleLineParser           |
                                            self.blankLineTerminationParser | 
                                            self.multilineCommand           +  
                                            pyparsing.SkipTo(
                                                stringEnd, 
                                                ignore=doNotParse) 
                                            )
        self.parser.ignore(self.commentGrammars)
        
        inputMark   = pyparsing.Literal('<')
        inputMark.setParseAction(lambda x: '')
        fileName    = pyparsing.Word(self.legalChars + '/\\')
        inputFrom   = fileName('inputFrom')
        inputFrom.setParseAction(replace_with_file_contents)
        # a not-entirely-satisfactory way of distinguishing < as in "import from" 
        # from < as in "lesser than"
        self.inputParser =  inputMark                     + \
                            pyparsing.Optional(inputFrom) + \
                            pyparsing.Optional('>')       + \
                            pyparsing.Optional(fileName)  + \
                            (pyparsing.stringEnd | '|')
        self.inputParser.ignore(self.commentInProgress)               
    
    def _cmdloop(self, intro=None):
        '''Repeatedly issue a prompt, accept input, parse an initial prefix
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
                readline.parse_and_bind(self.completekey+": complete")
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
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass    
            return stop

    def _default(self, statement):
        #   @FIXME
        #       Add DocString
        arg = statement.full_parsed_statement()
        if self.default_to_shell:
            result = os.system(arg)
            if not result:
                return self.postparsing_postcmd(None)
        return self.postparsing_postcmd(self.default(arg))

    def poutput(self, msg):
        '''Shortcut for self.stdout.write() (adds newline if necessary).'''
        if msg:
            self.stdout.write(msg)
            if msg[-1] is not '\n':
                self.stdout.write('\n')
    
    def perror(self, errmsg, statement=None):
        #   @FIXME
        #       Add DocString
        if self.debug:
            traceback.print_exc()
        print(str(errmsg))
    
    def pfeedback(self, msg):
        '''For printing nonessential feedback.  Can be silenced with `quiet`.
           Inclusion in redirected output is controlled by `feedback_to_output`.'''
        if not self.quiet:
            if self.feedback_to_output:
                self.poutput(msg)
            else:
                print(msg)
    
    def colorize(self, val, color):
        '''Given a string (``val``), returns that string wrapped in UNIX-style 
           special characters that turn on (and then off) text color and style.
           If the ``colors`` environment paramter is ``False``, or the application
           is running on Windows, will return ``val`` unchanged.
           
           ``color`` should be one of the supported strings (or styles):
           
            red/blue/green/cyan/magenta, bold, underline'''
        if self.colors and (self.stdout == self.initial_stdout):
            return  self.colorcodes[color][True] + \
                    val                          + \
                    self.colorcodes[color][False]
        return val

    def preparse(self, raw, **kwargs):
        #   @FIXME
        #       Add DocString
        return raw
    
    def postparse(self, parseResult):
        #   @FIXME
        #       Add DocString
        return parseResult
   
    #   @FIXME
    #       Refactor into parser module
    def parsed(self, raw, **kwargs):
        #   @FIXME
        #       Add DocString
        if isinstance(raw, ParsedString):
            p = raw
        else:
            # preparse is an overridable hook; default makes no changes
            s = self.preparse(raw, **kwargs)
            s = self.inputParser.transformString(s.lstrip())
            s = self.commentGrammars.transformString(s)
            for (shortcut, expansion) in self.shortcuts:
                if s.lower().startswith(shortcut):
                    s = s.replace(shortcut, expansion + ' ', 1)
                    break
            result              = self.parser.parseString(s)
            result['raw']       = raw            
            result['command']   = result.multilineCommand or result.command        
            result              = self.postparse(result)
            p               = ParsedString(result.args)
            p.parsed        = result
            p.parser        = self.parsed
        for (key, val) in kwargs:
            p.parsed[key] = val
        return p
              
    def postparsing_precmd(self, statement):
        #   @FIXME
        #       Add DocString
        stop = 0
        return stop, statement
    
    def postparsing_postcmd(self, stop):
        #   @FIXME
        #       Add DocString
        return stop
    
    #   @FIXME
    #       Shouldn't this method start with an underscore?
    def func_named(self, arg):
        #   @FIXME
        #       Add DocString
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
        '''Interpret the argument as though it had been typed in response
        to the prompt.

        This may be overridden, but should not normally need to be;
        see the precmd() and postcmd() methods for useful execution hooks.
        The return value is a flag indicating whether interpretation of
        commands by the interpreter should stop.
        
        This (`cmd2`) version of `onecmd` already overrides `cmd`'s `onecmd`.

        '''
        statement    = self.parsed(line)
        self.lastcmd = statement.parsed.raw   
        funcname     = self.func_named(statement.parsed.command)
        if not funcname:
            return self._default(statement)
        try:
            func    = getattr(self, funcname)
        except AttributeError:
            return self._default(statement)
        stop = func(statement) 
        return stop                
        
    def onecmd_plus_hooks(self, line):
        #   @FIXME
        #       Add DocString
        
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
                if statement.parsed.command not in self.excludeFromHistory:
                    self.history.append(statement.parsed.raw)      
                try:
                    self.redirect_output(statement)
                    timestart   = datetime.datetime.now()
                    statement   = self.precmd(statement)
                    stop    = self.onecmd(statement)
                    stop    = self.postcmd(stop, statement)
                    if self.timing:
                        self.pfeedback('Elapsed: %s' % 
                                        str(datetime.datetime.now() - timestart))
                finally:
                    self.restore_output(statement)
            except EmptyStatement:
                return 0
            except Exception, e:
                self.perror(str(e), statement)            
        finally:
            return self.postparsing_postcmd(stop)        
    
    def complete_statement(self, line):
        '''
        Keep accepting lines of input until the command is complete.
        '''
        #   @FIXME
        #       How is this different from Cmd.complete_statement() ?
        
        if (not line) or (
            not pyparsing.Or(self.commentGrammars).
                setParseAction(lambda x: '').transformString(line)):
            raise EmptyStatement
        statement = self.parsed(line)
        while statement.parsed.multilineCommand and \
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
                raise EnvironmentError('Cannot redirect to paste buffer; install ``xclip`` and re-run to enable')
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
        #   @FIXME
        #       TODO: not working on localhost
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
                                              self.defaultExtension), 
                                    'r')
        return result
        
    def pseudo_raw_input(self, prompt):
        '''Extracted from cmd's cmdloop. Similar to `raw_input()`, but 
        accounts for changed stdin / stdout'''
        
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
    
    def select(self, options, prompt='Your choice? '):
        '''Presents a numbered menu to the user.  Modelled after
           the bash shell's SELECT.  Returns the item chosen.
           
           Argument ``options`` can be:

             | a single string      -> will be split into one-word options
             | a list of strings    -> will be offered as options
             | a list of tuples     -> interpreted as (value, text), so 
                                       that the return value can differ from
                                       the text advertised to the user '''
        if isinstance(options, six.string_types):
            options = zip(options.split(), options.split())
        fulloptions = []
        for opt in options:
            if isinstance(opt, six.string_types):
                fulloptions.append((opt, opt))
            else:
                try:
                    fulloptions.append((opt[0], opt[1]))
                except IndexError:
                    fulloptions.append((opt[0], opt[0]))
        for (idx, (value, text)) in enumerate(fulloptions):
            self.poutput('  %2d. %s\n' % (idx+1, text))
        while True:
            response    = raw_input(prompt)
            try:
                response    = int(response)
                result      = fulloptions[response - 1][0]
                break
            except ValueError:
                pass # loop and ask again
        return result
    
    def last_matching(self, arg):
        #   @FIXME
        #       Add DocString
        try:
            if arg:
                return self.history.get(arg)[-1]
            else:
                return self.history[-1]
        except IndexError:
            return None        
    
    def fileimport(self, statement, source):
        #   @FIXME
        #       Add DocString
        try:
            f = open(os.path.expanduser(source))
        except IOError:
            self.stdout.write("Couldn't read from file %s\n" % source)
            return ''
        data = f.read()
        f.close()
        return data

    def run_commands_at_invocation(self, callargs):
        #   @FIXME
        #       Add DocString
        for initial_command in callargs:
            if self.onecmd_plus_hooks(initial_command + '\n'):
                return self._STOP_AND_EXIT

    def cmdloop(self):
        #   @FIXME
        #       Add DocString
        parser = optparse.OptionParser()
        parser.add_option(  '-t', 
                            '--test', 
                            dest    ='test',
                            action  ='store_true', 
                            help    ='Test against transcript(s) in FILE (wildcards OK)')
        (callopts, callargs) = parser.parse_args()
        if callopts.test:
            self.runTranscriptTests(callargs)
        else:
            if not self.run_commands_at_invocation(callargs):
                self._cmdloop() 
         
         
    #-----------------------------------------------------
    #   COMMANDS
    #   ========
    #   Only `do_*` commands from here to the end
    #   of the class.
    #-----------------------------------------------------
    def do_cmdenvironment(self, args):
        '''Summary report of interactive parameters.'''
        self.poutput('''
            Commands are %(casesensitive)scase-sensitive.
            Commands may be terminated with: %(terminators)s
            Settable parameters: %(settable)s\n''' % { 
                'casesensitive' : (self.case_insensitive and 'not ') or '',
                'terminators'   : str(self.terminators),
                'settable'      : ' '.join(self.settable)}
        )
        
    def do_help(self, arg):
        #   @FIXME
        #       Add DocString 
        #       (How is this different from Cmd.do_help() ?)
        if arg:
            funcname = self.func_named(arg)
            if funcname:
                fn  = getattr(self, funcname)
                try:
                    fn.optionParser.print_help(file=self.stdout)
                except AttributeError:
                    cmd.Cmd.do_help(self, funcname[3:])
        else:
            cmd.Cmd.do_help(self, arg)
        
    def do_shortcuts(self, args):
        '''Lists single-key shortcuts available.'''
        result = "\n".join('%s: %s' % 
                            (sc[0], sc[1]) for sc in sorted(self.shortcuts)
                        )
        self.stdout.write("Single-key shortcuts for other commands:\n%s\n" % (result))

    def do_EOF(self, arg):
        #   @FIXME
        #       Add DocString
        #       
        #       *   should this always/never be called under 
        #           certain circumstances?
        #       *   error codes? (e.g., "return 0 on success, >0 on error")
        #       *   signals? (SIGINT, SIGHUP, SIGEOF, etc.)
        return self._STOP_SCRIPT_NO_EXIT # End of script; should not exit app
    
    do_eof  = do_EOF

    def do_quit(self, arg):
        #   @FIXME
        #       Add DocString
        #       
        #       *   should this always/never be called under 
        #           certain circumstances?
        #       *   error codes? (e.g., "return 0 on success, >0 on error")
        #       *   signals? (SIGINT, SIGHUP, SIGEOF, etc.)
        return self._STOP_AND_EXIT
    
    do_exit = do_quit
    do_q    = do_quit

    @options([make_option(
                '-l', '--long', 
                action  ='store_true',
                help    ='describe function of parameter')])
    def do_show(self, arg, opts):
        '''Shows value of a parameter.'''
        param   = arg.strip().lower()
        result  = {}
        maxlen  = 0
        for p in self.settable:
            if (not param) or p.startswith(param):
                result[p]   = '%s: %s' % (p, str(getattr(self, p)))
                maxlen      = max(maxlen, len(result[p]))
        if result:
            for p in sorted(result):
                if opts.long:
                    self.poutput('%s # %s' % (result[p].ljust(maxlen), self.settable[p]))
                else:
                    self.poutput(result[p])
        else:
            raise NotImplementedError("Parameter '%s' not supported (type 'show' for list of parameters)." % param)
    
    def do_set(self, arg):
        '''
        Sets a cmd2 parameter.  Accepts abbreviated parameter names so long
        as there is no ambiguity.  Call without arguments for a list of 
        settable parameters with their values.
        '''
        try:
            statement, \
            paramName, \
            val         = arg.parsed.raw.split(None, 2)
            
            val         = val.strip()
            paramName   = paramName.strip().lower()
            if paramName not in self.settable:
                hits =  [p for p in self.settable 
                            if p.startswith(paramName)]
                if len(hits) is 1:
                    paramName = hits[0]
                else:
                    return self.do_show(paramName)
            currentVal = getattr(self, paramName)
            if (val[0] == val[-1]) and val[0] in ("'", '"'):
                val = val[1:-1]
            else:                
                val = cast(currentVal, val)
            setattr(self, paramName, val)
            self.stdout.write('%s - was: %s\nnow: %s\n' % 
                                (paramName, 
                                currentVal, 
                                val)
                            )
            if currentVal != val:
                try:
                    onchange_hook = getattr(self, '_onchange_%s' % paramName)
                    onchange_hook(old=currentVal, new=val)
                except AttributeError:
                    pass
        except (ValueError, AttributeError, NotSettableError), e:
            self.do_show( arg )
                
    def do_pause(self, arg):
        '''Displays the specified text then waits for the user to press RETURN.'''
        raw_input(arg + '\n')
        
    def do_shell(self, arg):
        '''Execute command as if at the OS prompt.'''
        os.system(arg)
                
    def do_py(self, arg):  
        '''
        py <command>: Executes a Python command.
        py: Enters interactive Python mode.
        
        End with ``Ctrl-D`` (Unix) / ``Ctrl-Z`` (Windows), ``quit()``, '`exit()``.
        
        Non-python commands can be issued with ``cmd("your command")``.
        
        Run python code from external files with ``run("filename.py")``
        '''
        self.pystate['self'] = self
        arg         = arg.parsed.raw[2:].strip()
        localvars   = (self.locals_in_py and self.pystate) or {}
        interp      = InteractiveConsole(locals=localvars)
        interp.runcode('import sys, os;sys.path.insert(0, os.getcwd())')
        if arg.strip():
            interp.runcode(arg)
        else:
            def quit():
                raise EmbeddedConsoleExit
            def onecmd_plus_hooks(arg):
                return self.onecmd_plus_hooks(arg + '\n')
            def run(arg):
                try:
                    file = open(arg)
                    interp.runcode(file.read())
                    file.close()
                except IOError, e:
                    self.perror(e)
            self.pystate['quit']    = quit
            self.pystate['exit']    = quit
            self.pystate['cmd']     = onecmd_plus_hooks
            self.pystate['run']     = run
            try:
                cprt        = 'Type "help", "copyright", "credits" or "license" for more information.'        
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
        '''history [arg]: lists past commands issued
        
        | no arg:         list all
        | arg is integer: list one history item, by index
        | arg is string:  string search
        | arg is /enclosed in forward-slashes/: regular expression search
        '''
        if arg:
            history = self.history.get(arg)
        else:
            history = self.history
        for hi in history:
            if opts.script:
                self.poutput(hi)
            else:
                self.stdout.write(hi.pr())
    
    def do_list(self, arg):
        '''list [arg]: lists last command issued
        
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
        for hi in history:
            self.poutput(hi.pr())

    do_hi   = do_history
    do_l    = do_list
    do_li   = do_list
        
    def do_ed(self, arg):
        '''
        ed: edit most recent command in text editor
        ed [N]: edit numbered command from history
        ed [filename]: edit specified file name
        
        commands are run after editor is closed.
        "set edit (program-name)" or set  EDITOR environment variable
        to control which editing program is used.
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
            f = open(os.path.expanduser(filename), 'w')
            f.write(buffer or '')
            f.close()        
                
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
            args = self.saveparser.parseString(arg)
        except pyparsing.ParseException:
            self.perror('Could not understand save target %s' % arg)
            raise SyntaxError(self.do_save.__doc__)
        fname = args.fname or self.default_file_name
        if args.idx == '*':
            saveme = '\n\n'.join(self.history[:])
        elif args.idx:
            saveme = self.history[int(args.idx)-1]
        else:
            saveme = self.history[-1]
        try:
            f = open(os.path.expanduser(fname), 'w')
            f.write(saveme)
            f.close()
            self.pfeedback('Saved to %s'  % (fname))
        except Exception, e:
            self.perror('Error saving %s' % (fname))
            raise
            
    def do__relative_load(self, arg=None):
        '''
        Runs commands in script at file or URL; if this is called from within an
        already-running script, the filename will be interpreted relative to the 
        already-running script's directory.
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
        '''Runs script of command(s) from a file or URL.'''
        if arg is None:
            targetname  = self.default_file_name
        else:
            arg         = arg.split(None, 1)
            targetname  = arg[0]
            arts        = (arg[1:] or [''])[0].strip()
        try:
            target = self.read_file_or_url(targetname)
        except IOError, e:
            self.perror('Problem accessing script from %s: \n%s' % (targetname, e))
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
        
        no arg                      -> run most recent command
        arg is integer              -> run one history item, by index
        arg is string               -> run most recent command by string search
        /arg in forward-slashes/    -> run most recent by regex
        '''
        'run [N]: runs the SQL that was run N commands ago'
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
into a file, ``transcript.test``, and invoke the test like::

    python myapp.py --test transcript.test

Wildcards can be used to test against multiple transcript files.
'''