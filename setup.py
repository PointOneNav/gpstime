from setuptools import setup


setup(
    setup_requires=[
        'setuptools_scm',
    ],
    use_scm_version={
        'write_to': 'gpstime/_version.py',
    },

    name='gpstime',
    description='GPS-aware datetime module',
    author='Jameson Graef Rollins',
    author_email='jameson.rollins@ligo.org',
    url='https://git.ligo.org/cds/gpstime',
    license='GNU GPL v3+',

    packages=['gpstime'],
    scripts=['bin/gpstime'],

    install_requires=[
        'python-dateutil',
        'requests',
    ],

    test_suite='gpstime.test',
)
