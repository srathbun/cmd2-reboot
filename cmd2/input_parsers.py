# -*- coding: UTF-8 -*-
'''The input_parser class is the default line parser for cmd2.'''
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

if not six.PY3:
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
#       Move to parsers module...without breaking
#       any code in this file
pyparsing.ParserElement.setDefaultWhitespaceChars(' \t')

class input_parser(object):
    '''This class accepts an input string, and returns a parsed representation.'''

    def __init__(self, currState):
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
        #   I have a very poor understanding of the parser's 
        #   control flow when the user types a command and hits ENTER,
        #   and until the author (or another pyparsing expert) 
        #   explains what's happening to me, I have to do silly 
        #   things like this. :-|
        #
        #   Of course, if the impossible happens and this code 
        #   gets cleaned up, then the variables will be restored to 
        #   proper capitalization.
        #
        #   —Zearin
        #   http://github.com/zearin
        #   2012 Mar 26

        #   ----------------------------
        #   QuickRef: Pyparsing Operators
        #   ----------------------------
        #   ~   creates NotAny using the expression after the operator
        #
        #   +   creates And using the expressions before and after the operator
        #
        #   |   creates MatchFirst (first left-to-right match) using the 
        #       expressions before and after the operator
        #
        #   ^   creates Or (longest match) using the expressions before and 
        #       after the operator
        #
        #   &   creates Each using the expressions before and after the operator
        #
        #   *   creates And by multiplying the expression by the integer operand; 
        #       if expression is multiplied by a 2-tuple, creates an And of 
        #       (min,max) expressions (similar to "{min,max}" form in 
        #       regular expressions); if min is None, intepret as (0,max); 
        #       if max is None, interpret as expr*min + ZeroOrMore(expr)
        #
        #   -   like + but with no backup and retry of alternatives
        #
        #   *   repetition of expression
        #
        #   ==  matching expression to string; returns True if the string 
        #       matches the given expression
        #
        #   <<  inserts the expression following the operator as the body of the 
        #       Forward expression before the operator
        #   ----------------------------

        #   Aliased for readability inside this method
        PYP = pyparsing

        #   ----------------------------
        #   Tell pyparsing how to parse 
        #   file input from '< filename'
        #   ----------------------------
        FILENAME    = PYP.Word(currState.legal_chars + '/\\')
        INPUT_MARK  = PYP.Literal('<')
        INPUT_MARK.setParseAction(lambda x: '')
        INPUT_FROM  = FILENAME('INPUT_FROM')
        INPUT_FROM.setParseAction(replace_with_file_contents)
        #   ----------------------------


        DO_NOT_PARSE            =   currState.comment_grammars       |   \
                                    currState.comment_in_progress    |   \
                                    PYP.quotedString

        #OUTPUT_PARSER = (PYP.Literal('>>') | (PYP.WordStart() + '>') | PYP.Regex('[^=]>'))('output')
        OUTPUT_PARSER           =  (PYP.Literal(   2 * currState.redirector) | \
                                   (PYP.WordStart()  + currState.redirector) | \
                                    PYP.Regex('[^=]' + currState.redirector))('output')

        PIPE                    =   PYP.Keyword('|', identChars='|')

        STRING_END              =   PYP.stringEnd ^ '\nEOF'

        TERMINATOR_PARSER       =   PYP.Or([
                                        (hasattr(t, 'parseString') and t)
                                        or PYP.Literal(t) for t in currState.terminators
                                    ])('terminator')

        #   moved here from class-level variable
        currState.URLRE              =   re.compile('(https?://[-\\w\\./]+)')

        currState.keywords           =   currState.reserved_words + [fname[3:] for fname in dir(self) if fname.startswith('do_')]

        currState.comment_grammars.ignore(PYP.quotedString).setParseAction(lambda x: '')

        #   not to be confused with `multiln_parser` (below)
        currState.multiline_command  =   PYP.Or([
                                        PYP.Keyword(c, caseless=currState.case_insensitive)
                                        for c in currState.multiline_commands
                                    ])('multiline_command')

        ONELN_COMMAND           =   (   ~currState.multiline_command +
                                        PYP.Word(currState.legal_chars)
                                    )('command')

        #ONELN_COMMAND.setDebug(True)

        #   CASE SENSITIVITY for 
        #   ONELN_COMMAND and self.multiline_command
        if currState.case_insensitive:
            #   Set parsers to account for case insensitivity (if appropriate)
            currState.multiline_command.setParseAction(lambda x: x[0].lower())
            ONELN_COMMAND.setParseAction(lambda x: x[0].lower())

        currState.save_parser        = ( PYP.Optional(PYP.Word(PYP.nums)^'*')('idx')
                                  + PYP.Optional(PYP.Word(currState.legal_chars + '/\\'))('fname')
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

        currState.multiln_parser = (((currState.multiline_command ^ ONELN_COMMAND)
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

        currState.multiln_parser.ignore(currState.comment_in_progress)

        currState.singleln_parser  = (
                                    (   ONELN_COMMAND + PYP.SkipTo(
                                        TERMINATOR_PARSER 
                                        ^ STRING_END 
                                        ^ PIPE 
                                        ^ OUTPUT_PARSER, 
                                        ignore=DO_NOT_PARSE
                                    ).setParseAction(lambda x:x[0].strip())('args'))('statement')
                                + PYP.Optional(TERMINATOR_PARSER)
                                + AFTER_ELEMENTS)
        #self.multiln_parser  = self.multiln_parser('multiln_parser')
        #self.singleln_parser = self.singleln_parser('singleln_parser')


        #   Configure according to `allow_blank_lines` setting
        if currState.allow_blank_lines:
            currState.blankln_termination_parser = PYP.NoMatch
        else:
            currState.blankln_terminator = (PYP.lineEnd + PYP.lineEnd)('terminator')
            currState.blankln_terminator('terminator')
            currState.blankln_termination_parser = (
                                                (currState.multiline_command ^ ONELN_COMMAND)
                                                + PYP.SkipTo(
                                                    currState.blankln_terminator,
                                                    ignore=DO_NOT_PARSE
                                                ).setParseAction(lambda x: x[0].strip())('args')
                                                + currState.blankln_terminator)('statement')

        currState.blankln_termination_parser = currState.blankln_termination_parser('statement')

        currState.parser = currState.prefix_parser + (STRING_END                      |
                                            currState.multiln_parser             |
                                            currState.singleln_parser            |
                                            currState.blankln_termination_parser |
                                            currState.multiline_command          +
                                            PYP.SkipTo(
                                                STRING_END, 
                                                ignore=DO_NOT_PARSE) 
                                            )

        currState.parser.ignore(currState.comment_grammars)
        # a not-entirely-satisfactory way of distinguishing
        # '<' as in "import from" from 
        # '<' as in "lesser than"
        currState.input_parser = INPUT_MARK                + \
                            PYP.Optional(INPUT_FROM)  + \
                            PYP.Optional('>')         + \
                            PYP.Optional(FILENAME)    + \
                            (PYP.stringEnd | '|')

        currState.input_parser.ignore(currState.comment_in_progress)
