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
import  collections,    \
        copy,           \
        functools,      \
        os,             \
        re,             \
        subprocess,     \
        sys,            \
        warnings


#   Third Party Imports
#   --------------------------------------------------------
#import pyparsing

#   Cmd2 Modules
#   --------------------------------------------------------
from    .errors     import  PASTEBUFF_ERR

__all__ =   [   'HistoryItem',
                'History',
                'Statekeeper',
                'stubbornDict',
                'can_clip',
                'cast',
                'ljust',
                'get_paste_buffer',
                'replace_with_file_contents',
                'write_to_paste_buffer'         ]             



if subprocess.mswindows:    
    '''
    Initializes the methods `get_paste_buffer` and `write_to_paste_buffer`
    appropriately for the platform.
    '''
    
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
            raise OSError, PASTEBUFF_ERR % ('pywin32', 'Download from http://sourceforge.net/projects/pywin32/')
        write_to_paste_buffer = get_paste_buffer
elif sys.platform == 'darwin':
    can_clip = False
    try:
        # test for pbcopy. (Should always be installed on OS X, AFAIK.)
        subprocess.check_call(  'pbcopy -help', 
                                shell   = True, 
                                stdout  = subprocess.PIPE, 
                                stdin   = subprocess.PIPE, 
                                stderr  = subprocess.PIPE)
        can_clip = True
    except (subprocess.CalledProcessError, OSError, IOError):
        #   @FIXME
        #       Under what circumstances might this be raised?
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
            raise OSError, PASTEBUFF_ERR % ('pbcopy', 'Error should not occur on OS X; part of the default installation')
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
            test_str  = 'Testing for presence of xclip.'
            xclipproc   = subprocess.Popen( 'xclip -sel clip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE)
            xclipproc.stdin.write(test_str)
            xclipproc.stdin.close()
            xclipproc   = subprocess.Popen( 'xclip -o -sel clip', 
                                            shell   = True, 
                                            stdout  = subprocess.PIPE, 
                                            stdin   = subprocess.PIPE)        
            if xclipproc.stdout.read() == test_str:
                can_clip = True
        except Exception: 
            #   Hate a bare Exception call, but exception 
            #   classes vary too much b/t stdlib versions
            pass
    except Exception:
        #   Something went wrong with xclip and we cannot use it
        pass 
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
            raise OSError, PASTEBUFF_ERR % ('xclip', 'On Debian/Ubuntu, install with "sudo apt-get install xclip"')
        write_to_paste_buffer = get_paste_buffer


class History(list):
    '''
    A list of HistoryItems that knows how to respond to user requests.
    '''
    
    #   @FIXME
    #       Consider adding:
    #       -   __str__
    #       -   __format__
    #       -   __repr__
    #       -   __unicode__ (for Python 2)
    
    RANGE_PATTERN    = re.compile(r'^\s*(?P<start>[\d]+)?\s*\-\s*(?P<end>[\d]+)?\s*$')
    SPAN_PATTERN     = re.compile(r'^\s*(?P<start>\-?\d+)?\s*(?P<separator>:|(\.{2,}))?\s*(?P<end>\-?\d+)?\s*$')
    
    def append(self, new_histitem):
        '''
        Appends `new_histitem` to the current History list.
        '''
        new_histitem     = HistoryItem(new_histitem)
        list.append(self, new_histitem)
        new_histitem.idx = len(self)
    
    def extend(self, new_histitem):
        '''
        Adds multiple items to the current History list.
        '''
        for item in new_histitem:
            self.append(item)
        
    def get(self, get_histitem=None, from_end=False):
        #   @FIXME
        #       Add DocString
        
        #   @FIXME
        #       Consider using `__getattr__()` or `__getattribute__()` 
        #       instead
        if not get_histitem:
            return self
        try:
            get_histitem = int(get_histitem)
            if get_histitem < 0:
                return self[:(-1 * get_histitem)]
            else:
                return [self[get_histitem-1]]
        except IndexError:
            return []
        except ValueError:
            range_result = self.RANGE_PATTERN.search(get_histitem)
            if range_result:
                start       = range_result.group('start') or None
                end         = range_result.group('start') or None
                if start:
                    start   = int(start) - 1
                if end:
                    end     = int(end)
                return self[start:end]
                
            get_histitem = get_histitem.strip()

            if get_histitem.startswith(r'/') and get_histitem.endswith(r'/'):
                finder = re.compile(    get_histitem[1:-1], 
                                        re.DOTALL    | 
                                        re.MULTILINE | 
                                        re.IGNORECASE)
                def isin(hist_item):
                    return finder.search(hist_item)
            else:
                def isin(hist_item):
                    return (get_histitem.lower() in hist_item.lowercase)
            return [itm for itm in self if isin(itm)]
    
    def search(self, target):
        #   @FIXME
        #       Add DocString
        target = target.strip()
        
        if len(target) > 1 and target[0] == target[-1] == '/':
            #   @FIXME
            #       Describe this conditional
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
        results = self.SPAN_PATTERN.search(raw)
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
        result  = self.zero_based_index(int(raw)) if raw else None
        return result
    
    def zero_based_index(self, onebased):
        '''
        Converts a one-based index (`onebased`) to a zero-based index.
        '''
        return (onebased - 1) if onebased > 0 else onebased


class HistoryItem(str):
    '''
    This extends `str` with a tweaked `print_` method.  Also preemptively 
    stores an index number and a lowercase version of itself.
    '''
    
    LISTFORMAT = '-------------------------[%d]\n%s\n'
    
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
        Prints the HistoryItem using a custom LISTFORMAT.
        '''
        return self.LISTFORMAT % (self.idx, str(self))
    

class Statekeeper:
    '''
    Saves and restores snapshots of a Python object's state.  Does not store
    data to the filesystem (i.e. doesn't use pickle).  
    
    Be careful!  Data is lost when Python execution stops.
    '''
    
    #   @FIXME
    #       Consider the following data persistence tools
    #       for enhancement/replacement of this class's
    #       role in cmd2.
    #
    #       *   pickling protocol
    #           http://docs.python.org/library/pickle.html#the-pickle-protocol
    #       *   shelve protocol
    #           http://docs.python.org/library/shelve.html
    #       *   PersistentDict
    #           http://code.activestate.com/recipes/576642/
    #       *   
    
    def __init__(self, obj, attribs):
        #   @FIXME
        #       Add DocString; what happens on __init__?
        self.obj        = obj
        self.attribs    = attribs
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
            for arg_item in arg:
                if not isinstance(arg_item, str):
                    raise TypeError, "arg_item list arguments to `to_dict()` must only contain strings!" 
                    
                arg_item = arg_item.strip()
                
                if arg_item:
                    key_val = arg_item.split(None, 1)
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
    '''
    Factory function for creating StubbornDict instances.
    StubbornDicts are dictionaries that tolerate many input formats.
    '''
    
    #   @FIXME
    #       Why have a factory method instead 
    #       putting this into `StubbornDict.__init__()`?
    result = {}
    for arg_item in arg:
        result.update(StubbornDict.to_dict(arg_item))
    result.update(kwarg)                      
    return StubbornDict(result)


def cast(current, new_val):
    '''
    Tries to force a new_val value into the same type as the current.
    '''
    typ = type(current)
    if typ == bool:
        try:
            return bool(int(new_val))
        except (ValueError, TypeError):
            pass    #   @FIXME: Why pass?
        try:
            new_val = new_val.lower()
        except:
            pass
        if (new_val == 'on')  or (new_val[0] in {'y','t'}):
            return True
        if (new_val == 'off') or (new_val[0] in {'n','f'}):
            return False
    else:
        try:
            return typ(new_val)
        except:
            pass
    print("Problem setting parameter (now %s) to %s; incorrect type?" 
            % (current, new_val))
    return current


def deprecated(func):
    '''
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    
    Source (2012-04-06): 
    http://wiki.python.org/moin/PythonDecoratorLibrary#Smart_deprecation_warnings_.28with_valid_filenames.2C_line_numbers.2C_etc..29
    '''
    
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn_explicit(
            "Call to deprecated function %(funcname)s." % {
                'funcname': func.__name__,
            },
            category=DeprecationWarning,
            filename=func.func_code.co_filename,
            lineno=func.func_code.co_firstlineno + 1
        )
        return func(*args, **kwargs)
    return new_func


def ljust(lyst, width, fillchar=' '):
    '''
    Works like `str.ljust()` for lists.
    '''
    if hasattr(lyst, 'ljust'):
        return lyst.ljust(width, fillchar)
    else:
        if len(lyst) < width:
            lyst = (lyst + [fillchar] * width)[:width]
        return lyst


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