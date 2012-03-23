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
import  collections, re


#   Third Party Imports
#   --------------------------------------------------------
#import pyparsing

#   Cmd2 Modules
#   --------------------------------------------------------
from    .parsers    import (OptionParser,
                            ParsedString)


class HistoryItem(str):
    '''
    This extends `str` with a tweaked `print_` method.  Also preemptively 
    stores a lowercase version of itself as well as an index number.
    '''
    
    listformat = '-------------------------[%d]\n%s\n'
    
    def __init__(self, instr):
        #   @FIXME
        #       Add docstring
        
        #   @FIXME
        #       Unused argument `instr`
        str.__init__(self)
        self.lowercase  = self.lower()
        self.idx        = None
    
    def print_(self):
        '''
        Prints the HistoryItem using a custom listformat.
        '''
        return self.listformat % (self.idx, str(self))
    
    #   @FIXME
    #       Consider adding:
    #       -   __str__
    #       -   __format__
    #       -   __repr__
    #       -   __unicode__ (for Python 2)


class History(list):
    '''
    A list of HistoryItems that knows how to respond to user requests.
    '''
    
    rangePattern    = re.compile(r'^\s*(?P<start>[\d]+)?\s*\-\s*(?P<end>[\d]+)?\s*$')
    spanpattern     = re.compile(r'^\s*(?P<start>\-?\d+)?\s*(?P<separator>:|(\.{2,}))?\s*(?P<end>\-?\d+)?\s*$')
    
    def append(self, new):
        new     = HistoryItem(new)
        list.append(self, new)
        new.idx = len(self)
        '''
        Appends `new_histitem` to the current History list.
        '''
    
    def extend(self, new):
        for n in new:
            self.append(n)
        '''
        Adds multiple items to the current History list.
        '''
        
    def get(self, getme=None, fromEnd=False):
        #   @FIXME
        #       Add DocString
        
        #   @FIXME
        #       Consider using `__getattr__()` or `__getattribute__()` 
        #       instead
        if not getme:
            return self
        try:
            getme = int(getme)
            if getme < 0:
                return self[:(-1 * getme)]
            else:
                return [self[getme-1]]
        except IndexError:
            return []
        except ValueError:
            rangeResult = self.rangePattern.search(getme)
            if rangeResult:
                start       = rangeResult.group('start') or None
                end         = rangeResult.group('start') or None
                if start:
                    start   = int(start) - 1
                if end:
                    end     = int(end)
                return self[start:end]
                
            getme = getme.strip()

            if getme.startswith(r'/') and getme.endswith(r'/'):
                finder = re.compile(    getme[1:-1], 
                                        re.DOTALL    | 
                                        re.MULTILINE | 
                                        re.IGNORECASE)
                def isin(hi):
                    return finder.search(hi)
            else:
                def isin(hi):
                    return (getme.lower() in hi.lowercase)
            return [itm for itm in self if isin(itm)]
    
    def search(self, target):
        #   @FIXME
        #       Add DocString
        target = target.strip()
        if len(target) > 1 and target[0] == target[-1] == '/':
            target  = target[1:-1]
        else:
            target  = re.escape(target)
        pattern = re.compile(target, re.IGNORECASE)
        return [s for s in self if pattern.search(s)]
        
    def span(self, raw):
        #   @FIXME
        #       Add DocString
        if raw.lower() in ('*', '-', 'all'):
            raw = ':'
        results = self.spanpattern.search(raw)
        if not results:
            raise IndexError
        if not results.group('separator'):
            return [self[self.to_index(results.group('start'))]]
        start   = self.to_index(results.group('start'))
        end     = self.to_index(results.group('end'))
        reverse = False
        if end is not None:
            if end < start:
                (start, end) = (end, start)
                reverse = True
            end += 1
        result = self[start:end]
        if reverse:
            result.reverse()
        return result
                
    def to_index(self, raw):
        '''
        Gets the index number of `raw`.
        '''
        if raw:
            result  = self.zero_based_index(int(raw))
        else:
            result  = None
        return result
    
    def zero_based_index(self, onebased):
        '''
        Converts a one-based index (`onebased`) to a zero-based index.
        '''
        result  = onebased
        if result > 0:
            result -= 1
        return result


class Statekeeper:
    '''
    Saves and restores snapshots of a Python object's state.  Does not store
    data to the filesystem (i.e. doesn't use pickle).  
    
    Be careful!  Data is lost when Python execution stops.
    '''
    
    #   @FIXME
    #       Add support for pickling protocol
    #       http://docs.python.org/library/pickle.html#the-pickle-protocol
    
    def __init__(self, obj, attribs):
        #   @FIXME
        #       Add DocString; what happens on __init__?
        self.obj    = obj
        self.attribs= attribs
        if self.obj:
            self.save()
    
    def save(self):
        #   @FIXME
        #       Add DocString
        for attrib in self.attribs:
            setattr(self, attrib, getattr(self.obj, attrib))
    
    def restore(self):
        #   @FIXME
        #       Add DocString
        if self.obj:
            for attrib in self.attribs:
                setattr(self.obj, attrib, getattr(self, attrib))


class StubbornDict(dict):
    '''
    Dictionary that tolerates many input formats.
    Create with the `stubbornDict(arg)` factory function.
    '''    
    def __add__(self, other):
        selfcopy = copy.copy(self)
        selfcopy.update(stubbornDict(other))
        return selfcopy
    
    def __iadd__(self, other):
        self.update(other)
        return self
    
    def __radd__(self, other):
        return self.__add__(other)
        
    def update(self, other):
        dict.update(self, StubbornDict.to_dict(other))
    
    append = update
    
    @classmethod
    def to_dict(cls, arg):
        '''
        Generates dictionary from a string or list of strings.
        '''
        result = {}
        
        if hasattr(arg, 'splitlines'):
            arg = arg.splitlines()
        
        #if isinstance(arg, list):
        if hasattr(arg, '__reversed__'):    
            for a in arg:
                if not isinstance(a, str):
                    raise TypeError, "A list arguments to `to_dict()` must only contain strings!" 
                    
                a = a.strip()
                
                if a:
                    key_val = a.split(None, 1)
                    key     = key_val[0]
                    
                    # print()
#                     print('{', key, ':', key_val, '}')
#                     print()
                    
                    if len( key_val ) > 1:
                        val = key_val[1]
                    else:
                        val = ''
                    result[key] = val
        else:
            result = arg
            
        return result


def stubbornDict(*arg, **kwarg):
    #   @FIXME
    #       Add DocString
    
    #   @FIXME
    #       Why have a factory method instead of 
    #       making this code into StubbornDict.__init__()?
    result = {}
    for a in arg:
        result.update(StubbornDict.to_dict(a))
    result.update(kwarg)                      
    return StubbornDict(result)


def cast(current, new):
    '''
    Tries to force a new value into the same type as the current.
    '''
    typ = type(current)
    if typ == bool:
        try:
            return bool(int(new))
        except (ValueError, TypeError):
            pass
        try:
            new = new.lower()    
        except:
            pass
        if (new == 'on')  or (new[0] in ('y','t')):
            return True
        if (new == 'off') or (new[0] in ('n','f')):
            return False
    else:
        try:
            return typ(new)
        except:
            pass
    print("Problem setting parameter (now %s) to %s; incorrect type?" 
            % (current, new))
    return current


def ljust(x, width, fillchar=' '):
    '''
    Works like `str.ljust()` for lists.
    '''
    if hasattr(x, 'ljust'):
        return x.ljust(width, fillchar)
    else:
        if len(x) < width:
            x = (x + [fillchar] * width)[:width]
        return x


def replace_with_file_contents(fname):
    #   @FIXME
    #       Add DocString
    if fname:
        try:
            result = open(os.path.expanduser(fname[0])).read()
        except IOError:
            result = '< %s' % fname[0]  # wasn't a file after all
    else:
        result = get_paste_buffer()
    return result