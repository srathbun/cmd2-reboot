# -*- coding: UTF-8 -*-
#   @FIXME
#       Add Docstring

#   __future__ first
from    __future__  import  (generators,
                            print_function,     
                            with_statement)


#   six: Python 2/3 Compatibility module
#   --------------------------------------------------------
#   Six should (after __future__) get imported first,
#   because it deals with the different standard libraries
#   between Python 2 and 3.
import  six


#   Standard Library Imports
#   --------------------------------------------------------
import  optparse,   \
        re


#   Third Party Imports
#   --------------------------------------------------------
#   argh includes argparse
import  argh,       \
        pyparsing

__all__ =   [   'OptionParser',
                'Parser',
                'ParsedString',
                'remaining_args',
                'options_defined',
                'options'
            ]

class OptionParser(optparse.OptionParser):
    '''
    A tweaked subclass of `optparse.OptionParser` to control output
    of help- and error-messages.
    '''
    
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


class ParsedString(str):
    #   @FIXME
    #       Add DocString
    def full_parsed_statement(self):
        #   @FIXME
        #       Add DocString
        new         =   ParsedString('%s %s' % (self.parsed.command, 
                                                self.parsed.args))
        new.parsed  =   self.parsed
        new.parser  =   self.parser
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
    
    pattern         = '\s+'.join( re.escape(a) for a in newarg_list ) + '\s*$'
    matching_obj    = re.search(pattern, oldargs)
    return oldargs[matching_obj.start():]


options_defined = [] # used to tell apart --options from SQL-style --comments


def options(option_list, arg_desc='arg'):
    '''
    Decorator function.  Use on a `cmd2` method (passing a list of 
    optparse-style options). This will populate the method's `opts` argument 
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
        opt_str = opt.get_opt_string()
        options_defined.append(pyparsing.Literal(opt_str))
    
    def option_setup(func):
        '''
        Does the option-setup and returns the decorated method.
        '''
        opt_parser = OptionParser()
        for opt in option_list:
            opt_parser.add_option(opt)
        opt_parser.set_usage("%s [options] %s" % ( func.__name__[3:], arg_desc) )
        opt_parser._func = func
        
        def new_func(instance, arg):
            '''
            Modifies the decorated function and returns it.
            '''
            try:
                opts, new_arglist = opt_parser.parse_args(arg.split())
                # Must find the remaining args in the original argument list, but 
                # mustn't include the command itself
                #if hasattr(arg, 'parsed') and new_arglist[0] == arg.parsed.command:
                #    new_arglist = new_arglist[1:]
                new_args = remaining_args(arg, new_arglist)
                if isinstance(arg, ParsedString):
                    arg = arg.with_args_replaced(new_args)
                else:
                    arg = new_args
            except optparse.OptParseError, err:
                print(err,"\n")
                opt_parser.print_help()
                return
            if hasattr(opts, '_exit'):
                return None
            return func(instance, arg, opts)
        
        new_func.__doc__ = '%s\n%s' % (func.__doc__, opt_parser.format_help())
        return new_func
    
    return option_setup
