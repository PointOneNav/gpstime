#!/usr/bin/env python

from distutils.core import setup

#execfile('lib/cdsutils/_version.py')

setup(
    name = 'gpstime',
    #version = __version__,
    version = '0.1',
    description = 'GPS aware datetime module',
    author = 'Jameson Graef Rollins',
    author_email = 'jameson.rollins@ligo.org',
    url = 'https://git.ligo.org/jameson.rollins/gpstime',
    license = 'GNU GPL v3+',
    
    py_modules = [
        'gpstime',
        ],

    scripts = ['gpstime'],
)
