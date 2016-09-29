#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'gpstime',
    version = '0.1.2',
    description = 'GPS-aware datetime module',
    author = 'Jameson Graef Rollins',
    author_email = 'jameson.rollins@ligo.org',
    url = 'https://git.ligo.org/jameson.rollins/gpstime',
    license = 'GNU GPL v3+',

    packages = ['gpstime'],

    package_data = {
        'gpstime': ['leap-seconds.list']
        },

    # install_requires = [
    #     'dateutil'
    #     ],

    test_suite = 'gpstime.test',

    entry_points = {
        'console_scripts': [
            'gpstime = gpstime:main',
            ],
        }
)
