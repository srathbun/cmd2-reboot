# -*- coding: UTF-8 -*-
#   @FIXME
#       Add docstring


#   __future__ first
from    __future__  import  generators,         \
                            print_function,     \
                            with_statement


#   Python 2/3 Compatibility
import  six


import  doctest,    \
        unittest,   \
        re,         \
        glob,       \
        sys
        
import  pyparsing


class Borg(object):
    '''
    All instances of any Borg subclass will share state.
    
    From Python Cookbook (2nd Edition), recipe 6.16.
    '''
    #   @FIXME
    #       Edit DocString to describe where Borg is 
    #       used in Cmd2, and where Cmd2 users may find it
    #       useful in their subclasses.
    
    _shared_state = {}

    #   @FIXME
    #       Use new-style Metaclasses
    #       
    #       -- OR --
    #
    #       Use six.with_metaclass; @see:
    #
    #       http://packages.python.org/six/#syntax-compatibility
    def __new__(cls, *a, **k):
        obj = object.__new__(cls, *a, **k)
        obj.__dict__ = cls._shared_state
        return obj


#   @FIXME
#       Refactor into dedicated test module    
class OutputTrap(Borg):
    '''
    Instantiate an OutputTrap to divert/capture ALL stdout output (for unit testing).
    Call `tearDown()` to return to normal output.
    '''
    def __init__(self):
        self.contents   = ''
        self.old_stdout = sys.stdout
        sys.stdout      = self
        
    def tearDown(self):
        sys.stdout      = self.old_stdout
        self.contents   = ''
    
    def read(self):
        result          = self.contents
        self.contents   = ''
        return result
        
    def write(self, txt):
        self.contents   += txt


#   @FIXME
#       Refactor into dedicated test module        
class Cmd2TestCase(unittest.TestCase):
    '''
    Subclass this (and set CmdApp) to make a `unittest.TestCase` class
    that will execute the commands in a transcript file and expect the results shown.
       
    See `example.py`.
    '''
    
    CmdApp = None
    
    regexPattern = pyparsing.QuotedString(  quoteChar       = r'/', 
                                            escChar         = '\\', 
                                            multiline       = True, 
                                            unquoteResults  = True)
    
    regexPattern.ignore(pyparsing.cStyleComment)
    notRegexPattern     = pyparsing.Word(pyparsing.printables)
    notRegexPattern.setParseAction(lambda t: re.escape(t[0]))
    expectationParser   = regexPattern | notRegexPattern
    anyWhitespace       = re.compile(r'\s', re.DOTALL | re.MULTILINE)
    
    def _test_transcript(self, fname, transcript):
        #   @FIXME 
        #       Add DocString
        lineNum     = 0
        finished    = False
        line        = transcript.next()
        lineNum     += 1
        tests_run   = 0
        while not finished:
            # Scroll forward to where actual commands begin
            while not line.startswith(self.cmdapp.prompt):
                try:
                    line = transcript.next()
                except StopIteration:
                    finished = True
                    break
                lineNum += 1
            command = [line[len(self.cmdapp.prompt):]]
            line    = transcript.next()
            # Read the entirety of a multi-line command
            while line.startswith(self.cmdapp.continuation_prompt):
                command.append(line[len(self.cmdapp.continuation_prompt):])
                try:
                    line = transcript.next()
                except StopIteration:
                    raise StopIteration, 'Transcript broke off while reading command beginning at line %d with\n%s' % (command[0])
                lineNum += 1
            command = ''.join(command)               
            # Send the command into the application and capture the resulting output
            stop    = self.cmdapp.onecmd_plus_hooks(command)
            #TODO: should act on `stop`
            result  = self.outputTrap.read()
            # Read the expected result from transcript
            if line.startswith(self.cmdapp.prompt):
                message = '\nFile %s, line %d\nCommand was:\n%s\nExpected: (nothing)\nGot:\n%s\n'%\
                    (fname, lineNum, command, result)     
                self.assert_(not(result.strip()), message)
                continue
            expected = []
            while not line.startswith(self.cmdapp.prompt):
                expected.append(line)
                try:
                    line    = transcript.next()
                except StopIteration:
                    finished= True                       
                    break
                lineNum     += 1
            expected = ''.join(expected)
            # Compare actual result to expected
            message     = '\nFile %s, line %d\nCommand was:\n%s\nExpected:\n%s\nGot:\n%s\n'%\
                (fname, lineNum, command, expected, result)      
            expected    = self.expectationParser.transformString(expected)
            # checking whitespace is a pain--let's skip it
            expected    = self.anyWhitespace.sub('', expected)
            result      = self.anyWhitespace.sub('', result)
            self.assert_(re.match(expected, result, re.MULTILINE | re.DOTALL), message)
    
    def setUp(self):
        #   @FIXME 
        #       Add DocString
        if self.CmdApp:
            self.outputTrap = OutputTrap()
            self.cmdapp     = self.CmdApp()
            self.fetchTranscripts()
    
    def tearDown(self):
        #   @FIXME 
        #       Add DocString
        if self.CmdApp:
            self.outputTrap.tearDown()
            
    def fetchTranscripts(self):
        #   @FIXME 
        #       Add DocString
        self.transcripts = {}
        for fileset in self.CmdApp.testfiles:
            for fname in glob.glob(fileset):
                tfile = open(fname)
                self.transcripts[fname] = iter(tfile.readlines())
                tfile.close()
        if not len(self.transcripts):
            raise StandardError,'No test files found; nothing to test.'
    
    def runTest(self): # was `testall`
        #   @FIXME 
        #       Add DocString
        if self.CmdApp:
            its = sorted(self.transcripts.items())
            for (fname, transcript) in its:
                self._test_transcript(fname, transcript)



def runTranscriptTests(self, callargs):
    #   @FIXME
    #       Add DocString
    class TestMyAppCase(Cmd2TestCase):
        CmdApp = self.__class__        
    self.__class__.testfiles = callargs
    sys.argv    = [sys.argv[0]] # the --test argument upsets unittest.main()
    testcase    = TestMyAppCase()
    runner      = unittest.TextTestRunner()
    result      = runner.run(testcase)
    result.printErrors()