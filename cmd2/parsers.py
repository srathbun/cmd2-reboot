# -*- coding: UTF-8 -*-
#   @FIXME
#       Add Docstring

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
import  optparse
import  re


#   Third Party Imports
#   --------------------------------------------------------
import  pyparsing


pyparsing.ParserElement.setDefaultWhitespaceChars(' \t')


__all__ =   [   'OptionParser',
                'ParsedString',
                'remaining_args',
                'options_defined',
                'options'
            ]

class OptionParser(optparse.OptionParser):
    #   @FIXME
    #       Add DocString
    
    #   @FIXME
    #       Consider supporting the contextmanager protocol 
    #       (adding `__enter__` and `__exit__` methods).
    #
    #       http://docs.python.org/reference/datamodel.html#with-statement-context-managers
    
    def __init__(self, *args, **kwargs):
        #   @FIXME
        #       Add DocString
        
        #   @FIXME
        #       
        optparse.OptionParser.__init__(self, *args, **kwargs)
    
    def exit(self, status=0, msg=None):
        #   @FIXME
        #       Add DocString
        self.values._exit = True
        if msg:
            print(msg)
            
    def print_help(self, *args, **kwargs):
        #   @FIXME
        #       Add DocString
        try:
            print(self._func.__doc__)
        except AttributeError:
            pass
        optparse.OptionParser.print_help(self, *args, **kwargs)

    def error(self, msg):
        '''
        error(msg : string)

        Prints a usage message incorporating `msg` to `stderr`, then exits.
        
        If you override this in a subclass, it should NOT return!
        It should exit *OR* raise an exception.
        '''
        raise optparse.OptParseError(msg)


class ParsedString(str):
    #   @FIXME
    #       Add DocString
    
    def full_parsed_statement(self):
        #   @FIXME
        #       Add DocString
        new        = ParsedString('%s %s' % (self.parsed.command, 
                                             self.parsed.args))
        new.parsed = self.parsed
        new.parser = self.parser
        return new       
    
    def with_args_replaced(self, newargs):
        #   @FIXME
        #       Add DocString
        new                          = ParsedString(newargs)
        new.parsed                   = self.parsed
        new.parser                   = self.parser
        new.parsed['args']           = newargs
        new.parsed.statement['args'] = newargs
        return new


def remaining_args(oldargs, newarg_list):
    '''
    Preserves argument's original spacing after removing options.
    '''
    #   @FIXME
    #       Consider moving inside the OptionParser class
    
    pattern     = '\s+'.join( re.escape(a) for a in newarg_list ) + '\s*$'
    matchObj    = re.search(pattern, oldargs)
    return oldargs[matchObj.start():]


options_defined = [] # used to tell apart --options from SQL-style --comments


def options(option_list, arg_desc='arg'):
    '''
    Decorator function.  Use on a `cmd2` method (passing a list of 
    optparse-style options) to populate the method's `opts` argument 
    from its raw text argument.

    For example, transform this:
       
        def do_something(self, arg):

    ...into this:
    
       @options([make_option('-q', '--quick', action='store_true',
                 help='Makes things fast')],
                 'source dest')
       def do_something(self, arg, opts):
           if opts.quick:
               self.fast_button = True
    '''
    #   @FIXME
    #       I *think* that this function is the only place where 
    #       the `OptionParser` class above is used.  All other places 
    #       use `optparse.OptionParser` instead.
    #
    #       So:
    #       *   Why is this?
    #       *   Should we convert existing uses of `optparse.OptionParser` 
    #           to the `OptionParser` class above?
    
    if not isinstance(option_list, list):
        option_list = [option_list]
    
    for opt in option_list:
        optstr = opt.get_opt_string()
        options_defined.append(pyparsing.Literal(optstr))
    
    def option_setup(func):
        optionParser = OptionParser()
        for opt in option_list:
            optionParser.add_option(opt)
        optionParser.set_usage("%s [options] %s" % ( func.__name__[3:], arg_desc) )
        optionParser._func = func
        
        def new_func(instance, arg):
            try:
                opts, newArgList = optionParser.parse_args(arg.split())
                # Must find the remaining args in the original argument list, but 
                # mustn't include the command itself
                #if hasattr(arg, 'parsed') and newArgList[0] == arg.parsed.command:
                #    newArgList = newArgList[1:]
                newArgs = remaining_args(arg, newArgList)
                if isinstance(arg, ParsedString):
                    arg = arg.with_args_replaced(newArgs)
                else:
                    arg = newArgs
            except optparse.OptParseError, e:
                print(e,"\n")
                optionParser.print_help()
                return
            if hasattr(opts, '_exit'):
                return None
            result = func(instance, arg, opts)                            
            return result        
        new_func.__doc__ = '%s\n%s' % (func.__doc__, optionParser.format_help())
        return new_func
    
    return option_setup