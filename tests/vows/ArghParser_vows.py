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

import  argparse,\
        collections,\
        optparse

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

import  argh,       \
        pyparsing


from    cmd2            import  *
from    cmd2.cmd2       import  Cmd
from    cmd2.parsers    import (OptionParser,
                                Parser,
                                ParsedString,   
                                remaining_args)

###     END IMPORTS     ###


#
#   BEGIN ZE TESTING! 
#===================================================================



@Vows.batch
class ArghParserVows(Vows.Context):
        def topic(self):
            return Parser()
            
        def should_be_instance_of_ArghParser(self, topic):
            expect(topic).to_be_instance_of(argh.ArghParser)
            
        def should_be_instance_of_argparse(self, topic):
            expect(topic).to_be_instance_of(argparse.ArgumentParser)
            
        def blah(self, topic):
            pass