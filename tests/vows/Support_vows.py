#!/usr/bin/env pyvows
# -*- coding: UTF-8 -*-
'''
    This file contains tests for what **WILL BE** cmd2's 
    "support" module.  
    
    The "support" module (once cmd2 is refactored) should 
    include everything in Cmd2 besides:
    
        * the main cmd2 module itself
        * parsers
        * settings
        * commands
        * or tests
'''
###     IMPORTS          ###      
#   Convenience, forward-compatibility
from __future__ import  generators,         \
                        print_function
import collections
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

from    cmd2            import  *
from    cmd2.support    import (HistoryItem ,
                                History     ,
                                Statekeeper ,
                                StubbornDict,
                                stubbornDict,
                                cast        ,
                                ljust       ,
                                pastebufferr)


###     END IMPORTS     ###


#
#   BEGIN ZE TESTING! 
#===================================================================


#   This is testdata, which is used in the tests that follow it.
#   
#   Please keep all test data separate from the tests themselves!
#   
#   @see
#        http://heynemann.github.com/pyvows/#-using-generative-testing
test_data = {
    'History': {
        'input': [
            HistoryItem('first'), 
            HistoryItem('second'), 
            HistoryItem('third'), 
            HistoryItem('fourth')],
    
        'span-results': {
            '-2..'  : ['third', 'fourth'],
            '2..3'  : ['second', 'third'],
            '3'     : ['third'],
            ':'     : ['first', 'second', 'third', 'fourth'],
            '2..'   : ['second', 'third', 'fourth'],
            '-1'    : ['fourth'],
            '-2..-3': ['third', 'second']},
    
        'search-results':   {
            'o'     :['second', 'fourth'],
            '/IR/'  :['first', 'third']}
    },
    
    'stubbornDictFactory' : (
        {   
            'input':    '''cow a bovine
                        horse an equine''',
            'output':   [('cow', 'a bovine'), ('horse', 'an equine')]
        },
        {
            'input':    ['badger', 'porcupine a poky creature'],
            'output':   [('badger', ''), ('porcupine', 'a poky creature')]
        },
        {
            'input':    {'turtle':'has shell', 'frog':'jumpy'},
            'output':   [('frog', 'jumpy'), ('turtle', 'has shell')]
        }
    )
}



    

@Vows.batch
class DocTestsConversion(Vows.Context):
    '''
    This Vows Batch should only contain tests converted from
    the DocTests from version 0.6.4.
    '''
    
    class TestHistory(Vows.Context):
        '''
        Tests the History class using the data and expected results
        from the legacy DocTests.
        '''
        def topic(self):
            return History( test_data['History']['input'] )

        def span_results_should_match(self, topic):
            for spanArg, result in test_data['History']['span-results'].iteritems():
                expect( topic.span(spanArg) ).to_equal( result )

        def search_results_should_match(self, topic):
            for searchArg, result in test_data['History']['search-results'].iteritems():
                expect( topic.search(searchArg) ).to_equal(result)


    class TestStubbornDict(Vows.Context):
        '''
        Tests the StubbornDict class using the data and expected results
        from the legacy DocTests.
        '''

        def topic(self):
            return StubbornDict(large='gross', small='klein')

        def test_sorted(self, topic):
            expect( sorted(topic.items()) ).to_equal( 
                [('large', 'gross'), ('small', 'klein')]
            )

        def should_be_type_StubbornDict(self, topic):
            expect( type(topic) ).to_equal( type(StubbornDict()) )


        class AppendAListOfValues(Vows.Context):
            def topic(self, parent):
                parent.update(['plain', '  plaid'])
                tpc = parent
                return tpc

            def should_have_type_StubbornDict(self, topic):
                expect( type(topic) ).to_equal( type(StubbornDict()) )

            def test_sorted_items(self, topic):
                expect( sorted(topic.items()) ).to_equal([
                    ('large', 'gross'), 
                    ('plaid', ''), 
                    ('plain', ''), 
                    ('small', 'klein')
                ])


                class IAddTripleQuotedString(Vows.Context):  
                    def topic(self, parent):
                        to_be_appended = '''girl Frauelein, Maedchen
                                            shoe schuh
                                         '''
                        parent.__iadd__(to_be_appended)
                        tpc = parent
                        return tpc
                        
                    def should_have_type_StubbornDict(self, topic):
                        expect( type(topic) ).to_equal( type(StubbornDict()) )

                    def test_sorted_items(self, topic):
                        expect( sorted(topic.items()) ).to_equal([
                            ('girl', 'Frauelein, Maedchen'),
                            ('large', 'gross'),
                            ('plaid', ''),
                            ('plain', ''),
                            ('shoe', 'schuh'),
                            ('small', 'klein')
                        ])

    
    class TestStubbornDictFactory(Vows.Context):
        def topic(self):
            return test_data['stubbornDictFactory']
            
        def test_input_matches_output(self, topic):
            for item in topic:
                if isinstance(item['input'], dict):
                    sDict = stubbornDict( **item['input'] )
                else:
                    sDict = stubbornDict(item['input'])
                expect( sorted(sDict.items()) ).to_equal( item['output'] )