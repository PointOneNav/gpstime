#!/usr/bin/env python

from distutils.core import setup

setup(
    name = 'gpstime',
    version = '0.1.0',
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
