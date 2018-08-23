#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'gpstime',
    version = '0.3.1',
    description = 'GPS-aware datetime module',
    author = 'Jameson Graef Rollins',
    author_email = 'jameson.rollins@ligo.org',
    url = 'https://git.ligo.org/cds/gpstime',
    license = 'GNU GPL v3+',

    packages = ['gpstime'],
    py_modules = ['ietf_leap_seconds'],

    install_requires = [
        'python-dateutil',
        'requests',
    ],

    test_suite = 'gpstime.test',

    # https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
    entry_points = {
        'console_scripts': [
            'gpstime = gpstime.__main__:main',
            'ietf-leap-seconds = ietf_leap_seconds:main',
            ],
        }
)
