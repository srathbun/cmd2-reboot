#!/usr/bin/env pyvows
# -*- coding: UTF-8 -*-
'''
    This file contains tests for what **WILL BE** cmd2's 
    "parser" module.  
    
    The "parser" module (once cmd2 is refactored) should 
    include everything in Cmd2 related to parsing.
'''

###     IMPORTS          ###      
#   Convenience, forward-compatibility
from __future__ import  generators,         \
                        print_function

import  collections
import  optparse

# try:
#     import six  #   single-source Python 2/3 helper
# except ImportError, e:
#     print(u'''  Couldn’t import module "six".  
#                 
#                 Fixing this problem will make the rest of life easier.  
#                 
#                 Really.  You should totally try to fix this first.
#         ''')

from    pyvows  import (Vows, expect)

import  pyparsing

from    cmd2            import  *
from    cmd2.cmd2       import  Cmd
from    cmd2.parsers    import  OptionParser,   \
                                ParsedString,   \
                                remaining_args

###     END IMPORTS     ###


#
#   BEGIN ZE TESTING! 
#===================================================================



def parsed_input(input, topic):
    #   Utility function for use in tests below.
    output = topic.parser.parseString(input).dump()
    return output


@Vows.batch
class DocTestVows(Vows.Context):
    class TestCmd_init_parser(Vows.Context):
        '''
        This Vows Batch should only contain tests converted from
        the DocTests from version 0.6.4.
        '''

        def topic(self):
            c = Cmd()
            c.multiline_commands = ['multiline']
            c.case_insensitive  = True
            c._init_parser()
            return c
            
        def test_topic(self, topic):
            expect(topic).to_be_instance_of(Cmd)
        
        def test_empty_string(self, topic):
            output = parsed_input('',topic)
            expect(output).to_equal('[]')
    
        def test_empty_command(self, topic):
            output = parsed_input('/* empty command */',topic)
            expect(output).to_equal('[]')
    
        def test_plainword(self, topic):
            output = parsed_input('plainword', topic)
            expect(output).to_equal(
'''['plainword', '']
- command: plainword
- statement: ['plainword', '']
  - command: plainword''')
    
        def test_termbare(self, topic):
            output = parsed_input('termbare;',topic)
            expect(output).to_equal(
'''['termbare', '', ';', '']
- command: termbare
- statement: ['termbare', '', ';']
  - command: termbare
  - terminator: ;
- terminator: ;''')
            
        def test_termbare_suffix(self, topic):
            output = parsed_input('termbare; suffx', topic)
            expect(output).to_equal(
'''['termbare', '', ';', 'suffx']
- command: termbare
- statement: ['termbare', '', ';']
  - command: termbare
  - terminator: ;
- suffix: suffx
- terminator: ;''')
            
        def test_barecommand(self, topic):
            output = parsed_input('barecommand',topic)
            expect(output).to_equal(
'''['barecommand', '']
- command: barecommand
- statement: ['barecommand', '']
  - command: barecommand''')
    
        def test_command_with_args(self, topic):
            output = parsed_input('COMmand with args',topic)
            expect(output).to_equal(
'''['command', 'with args']
- args: with args
- command: command
- statement: ['command', 'with args']
  - args: with args
  - command: command''')
    
        def test_command_with_args_and_terminator_and_suffix(self, topic):
            output = parsed_input('command with args and terminator; and suffix',topic)
            expect(output).to_equal(
'''['command', 'with args and terminator', ';', 'and suffix']
- args: with args and terminator
- command: command
- statement: ['command', 'with args and terminator', ';']
  - args: with args and terminator
  - command: command
  - terminator: ;
- suffix: and suffix
- terminator: ;''')
    
        def test_simple_piped(self, topic):
            output = parsed_input('simple | piped',topic)
            expect(output).to_equal(
'''['simple', '', '|', ' piped']
- command: simple
- pipeTo:  piped
- statement: ['simple', '']
  - command: simple''')
    
        def test_double_pipe_is_not_a_pipe(self, topic):
            output = parsed_input('double-pipe || is not a pipe',topic)
            expect(output).to_equal(
'''['double', '-pipe || is not a pipe']
- args: -pipe || is not a pipe
- command: double
- statement: ['double', '-pipe || is not a pipe']
  - args: -pipe || is not a pipe
  - command: double''')
    
        def test_command_with_args_terminator_suffix_piped(self, topic):
            output = parsed_input('command with args, terminator;sufx | piped',topic)
            expect(output).to_equal(
'''['command', 'with args, terminator', ';', 'sufx', '|', ' piped']
- args: with args, terminator
- command: command
- pipeTo:  piped
- statement: ['command', 'with args, terminator', ';']
  - args: with args, terminator
  - command: command
  - terminator: ;
- suffix: sufx
- terminator: ;''')
    
        def test_output_into_a_file(self, topic):
            output = parsed_input('output into > afile.txt',topic)
            expect(output).to_equal(
'''['output', 'into', '>', 'afile.txt']
- args: into
- command: output
- output: >
- outputTo: afile.txt
- statement: ['output', 'into']
  - args: into
  - command: output''')
    
        def test_output_into_sufx_piped_command_file(self, topic):
            output = parsed_input('output into;sufx | pipethrume plz > afile.txt',topic)
            expect(output).to_equal(
'''['output', 'into', ';', 'sufx', '|', ' pipethrume plz', '>', 'afile.txt']
- args: into
- command: output
- output: >
- outputTo: afile.txt
- pipeTo:  pipethrume plz
- statement: ['output', 'into', ';']
  - args: into
  - command: output
  - terminator: ;
- suffix: sufx
- terminator: ;''')
    
        def test_output_to_paste_buffer(self, topic):
            output = parsed_input('output to paste buffer >> ',topic)
            expect(output).to_equal(
'''['output', 'to paste buffer', '>>', '']
- args: to paste buffer
- command: output
- output: >>
- statement: ['output', 'to paste buffer']
  - args: to paste buffer
  - command: output''')
    
        def test_ignore_the_commented_stuff(self, topic):
            output = parsed_input('ignore the /* commented | > */ stuff;',topic)
            expect(output).to_equal(
'''['ignore', 'the /* commented | > */ stuff', ';', '']
- args: the /* commented | > */ stuff
- command: ignore
- statement: ['ignore', 'the /* commented | > */ stuff', ';']
  - args: the /* commented | > */ stuff
  - command: ignore
  - terminator: ;
- terminator: ;''')
    
        def test_redirect_output(self, topic):
            output = parsed_input('has > inside;',topic)
            expect(output).to_equal(
'''['has', '> inside', ';', '']
- args: > inside
- command: has
- statement: ['has', '> inside', ';']
  - args: > inside
  - command: has
  - terminator: ;
- terminator: ;''')
    
        def test_multiline_has_redirect_inside_unfinished_command(self, topic):
            output = parsed_input('multiline has > inside an unfinished command',topic)
            expect(output).to_equal(
'''['multiline', ' has > inside an unfinished command']
- multiline_command: multiline''')
    
        def test_multiline_has_redirect_inside(self, topic):
            output = parsed_input('multiline has > inside;',topic)
            expect(output).to_equal(
'''['multiline', 'has > inside', ';', '']
- args: has > inside
- multiline_command: multiline
- statement: ['multiline', 'has > inside', ';']
  - args: has > inside
  - multiline_command: multiline
  - terminator: ;
- terminator: ;''')
        
        def test_multiline_command_with_comment_in_progress(self, topic):
            output = parsed_input(r'multiline command /* with comment in progress;',topic)
            expect(output).to_equal(
'''['multiline', ' command /* with comment in progress;']
- multiline_command: multiline''')
    
        def test_multiline_command_with_complete_comment(self, topic):
            output = parsed_input('multiline command /* with comment complete */ is done;',topic)
            expect(output).to_equal(
'''['multiline', 'command /* with comment complete */ is done', ';', '']
- args: command /* with comment complete */ is done
- multiline_command: multiline
- statement: ['multiline', 'command /* with comment complete */ is done', ';']
  - args: command /* with comment complete */ is done
  - multiline_command: multiline
  - terminator: ;
- terminator: ;''')
    
        def test_multiline_command_ends(self, topic):
            output = parsed_input('multiline command ends\n\n',topic)
            expect(output).to_equal(
r'''['multiline', 'command ends', '\n', '\n']
- args: command ends
- multiline_command: multiline
- statement: ['multiline', 'command ends', '\n', '\n']
  - args: command ends
  - multiline_command: multiline
  - terminator: ['\n', '\n']
- terminator: ['\n', '\n']''')
    
        def test_multiline_command_with_term_ends(self, topic):
            output = parsed_input('multiline command "with term; ends" now\n\n',topic)
            expect(output).to_equal(
r'''['multiline', 'command "with term; ends" now', '\n', '\n']
- args: command "with term; ends" now
- multiline_command: multiline
- statement: ['multiline', 'command "with term; ends" now', '\n', '\n']
  - args: command "with term; ends" now
  - multiline_command: multiline
  - terminator: ['\n', '\n']
- terminator: ['\n', '\n']''')
    
        def test_if_quoted_strings_seem_to_start_comments(self, topic):
            output = parsed_input('what if "quoted strings /* seem to " start comments?',topic)
            expect(output).to_equal(
'''['what', 'if "quoted strings /* seem to " start comments?']
- args: if "quoted strings /* seem to " start comments?
- command: what
- statement: ['what', 'if "quoted strings /* seem to " start comments?']
  - args: if "quoted strings /* seem to " start comments?
  - command: what''')

    
    class TestRemainingArgs(Vows.Context):
        def topic(self):
            return remaining_args('-f bar   bar   cow', ['bar', 'cow'])
            
        def expected_results(self, topic):
            expect(topic).to_equal('bar   cow')
            

@Vows.batch
class ParserVows(Vows.Context):
    
    
    class OptionParserVows(Vows.Context):
        def topic(self):
            return OptionParser()
            
        def should_be_optparse_parser(self, topic):
            expect(isinstance(topic,optparse.OptionParser)).to_be_true()
            
            
    class ParsedStringVows(Vows.Context):
        def topic(self):
            return ParsedString()
            
        def should_be_string(self, topic):
            expect(isinstance(topic,str)).to_be_true()
        
        def should_be_instance_of_ParsedString(self, topic):
            expect(topic).to_be_instance_of(ParsedString)