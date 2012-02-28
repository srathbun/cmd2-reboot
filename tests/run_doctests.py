#!/usr/bin/env python -B
'''Runs all tests in the `doctests` directory.

NOTE:
    In order for the tests to pass, the PYTHONPATH
    environment variable needs to look in the 
    parent directory (`..`).  
'''
import  doctest

import  cmd2
from    cmd2    import  Cmd,            \
                        History,        \
                        remaining_args, \
                        stubbornDict,   \
                        StubbornDict


if __name__ == '__main__':
    import os
    
    def testargs( filename ):
        return {'filename'       : 'doctests/' + filename,
                'module_relative': True,
                #'name'           : ,
                #'package'        : ,
                #'globs'          : ,
                'verbose'        : False,
                'report'         : True,
                #'optionflags'    : doctest.NORMALIZE_WHITESPACE,
                #'extraglobs'     : ,
                'raise_on_error' : False,
                #'parser'         : ,
                 'encoding'       : 'UTF-8'
                }
    
    for file in os.listdir( 'doctests' ):
        print "\n"
        print str(file).upper().center(70)
        doctest.testfile( **testargs(file) )