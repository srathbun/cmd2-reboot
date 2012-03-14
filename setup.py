#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup
    def find_packages():
        return ['sqlpython']
import sys

install_requires = ['pyparsing>=1.5.6']
long_description = '''Enhancements for standard library's ``cmd`` module.

This drop-in replacement adds several features for command-prompt tools:

    * Searchable command history (commands: "hi", "li", "run")
    * Load commands from file, save to file, edit commands in file
    * Multi-line commands
    * Case-insensitive commands
    * Accepts abbreviated commands when unambiguous
    * Parse commands with flags
    * Special-character shortcut commands beyond cmd's ``@`` and ``!``
    * Settable environment parameters
    * ``> _filename_``, ``>> _filename_``: redirect output to _filename_
    * ``< _filename_``: get input from _filename_
    * ``>``, ``>>``, ``<`` (without a filename): Redirect to/from the paste buffer
    * ``py`` enters interactive Python console
    * Test apps against sample session transcript (see example/example.py)

Usable without modification anywhere ``cmd`` is used. Simply ``import cmd2.Cmd`` in place of ``cmd.Cmd``.

Running `2to3 <http://docs.python.org/library/2to3.html>` against ``cmd2.py`` 
generates working, Python3-based code.

Documentation:
http://packages.python.org/cmd2/
'''

setup(
    name        =   'cmd2',
    version     =   '0.6.5',
    py_modules  =   ['cmd2'],
    use_2to3    =   True,
    
    # metadata for upload to PyPI
    author              =   'Catherine Devlin',
    author_email        =   'catherine.devlin@gmail.com',
    description         =   '''Extra features for standard library's cmd module''',
    license             =   'MIT',
    keywords            =   'command prompt console cmd shell cli',
    url                 =   'http://packages.python.org/cmd2/',
    install_requires    =   install_requires,
    long_description    =   long_description,
    classifiers         =   [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Programming Language :: Python 3',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    )

