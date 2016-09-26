#!/usr/bin/env python
"""datetime with GPS time support

This module primarily provides functions for converting to/from UNIX
and GPS times, as well as a `gpstime` class that directly inherits
from the builtin `datetime` class, adding additional methods for GPS
time input and output.

LEAPSECONDS: GPS time does not honor leap seconds.  In order to
translate between GPS and UNIX time all leap seconds since GPS time
zero need to be accounted for.  In this module, leap seconds are
determined by querying the IETF leap second bulletin:

  https://www.ietf.org/timezones/data/leap-seconds.list

Upon import, this module loads and parses a local cache of the
bulletin file, found in one of the following paths:

  ~/.cache/gpstime/leap-seconds.list
  /var/cache/gpstime/leap-seconds.list

If the found file is out of date the module will attempt to download
the latest version from the above URL, and store the updated file in
the user cache location.  System administrators may wish to keep an
up-to-date version at the system cache location.  The environment
variable IETF_LEAPFILE may be used to specify a bulletin file directly
and bypass any potential network access.

KNOWN BUGS: This module does not currently handle conversions of time
strings describing the actual leap second themselves, which are
usually represented as the 60th second of the minute during which the
leap second occurs.

"""

from __future__ import print_function
import os
import sys
import time
import urllib
from datetime import datetime
import dateutil
import warnings
import subprocess
from dateutil.tz import tzutc, tzlocal

import pkg_resources
try:
    __version__ = pkg_resources.require('gpstime')[0].version
except:
    __version__ = '?.?.?'

##################################################

ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

##################################################

# UNIX time for GPS 0 (1980-01-06T00:00:00Z)
GPS0 = 315964800
LEAPFILE_IETF = 'https://www.ietf.org/timezones/data/leap-seconds.list'
LEAPFILE_USER = os.path.expanduser('~/.cache/gpstime/leap-seconds.list')
LEAPFILE_SYS = '/var/cache/gpstime/leap-seconds.list'

def __ietf_c_to_unix(c):
    '''Convert time since century to time since UNIX epoch

    1900-01-01T00:00:00Z -> 1970-01-01T00:00:00Z
    '''
    return int(c) - 2208988800

def __ietf_update_file(path):
    '''Download IETF leap second data to path

    '''
    print('updating leap second data from IETF...', file=sys.stderr)
    urllib.urlretrieve(LEAPFILE_IETF, path+'.tmp')
    os.rename(path+'.tmp', path)

def __ietf_parse_leapfile(leapfile):
    '''Parse leap second data from IETF leap-seconds.list file

    https://www.ietf.org/timezones/data/leap-seconds.list
    '''
    data = []
    with open(leapfile) as f:
        for line in f:
            if line[:2] == '#@':
                expire = __ietf_c_to_unix(line.split()[1])
            elif line[0] == '#':
                pass
            else:
                sl = line.split()
                unix = __ietf_c_to_unix(sl[0])
                offset = int(sl[1])
                #print('%s -> %s, %s %s %s' % (sl[0], unix, offset, datetime.fromtimestamp(unix, tzutc()), sl[3:]))
                if unix > GPS0:
                    data.append((unix, offset))
    return data, expire

def __ietf_get_uptodate():
    '''Get up-to-date IETF leap second data

    Looks in user and system cache locations for IETF
    leap-seconds.list, then updates the user cache if no files could
    be found or were all expired.

    '''
    # first look in user and system locations
    for path in [LEAPFILE_USER, LEAPFILE_SYS]:
        if os.path.isfile(path):
            data, expire = __ietf_parse_leapfile(path)
            if expire >= time.time():
                #print(path, file=sys.stderr)
                return data
    # all files either don't exist or are expired, so update user data
    # from IETF
    try:
        dd = os.path.dirname(LEAPFILE_USER)
        if not os.path.exists(dd):
            os.makedirs(dd)
        __ietf_update_file(LEAPFILE_USER)
    except:
        pass
    data, expire = __ietf_parse_leapfile(LEAPFILE_USER)
    if expire < time.time():
        print('WARNING: leap second data is expired, and could not be updated from the IETF', file=sys.stderr)
    return data

LEAPDATA = __ietf_get_uptodate()
# FIXME: check expire on execution

##################################################

def unix2gps(unix):
    """Convert UNIX timestamp to GPS time.

    """
    unix = float(unix)
    gps = unix - GPS0
    for leap, offset in LEAPDATA:
        if unix < leap:
            break
        gps += 1
    return gps

def gps2unix(gps):
    """Convert GPS time to UNIX timestamp.

    """
    gps = float(gps)
    unix = gps + GPS0
    for leap, offset in LEAPDATA:
        if unix < leap:
            break
        unix -= 1
    return unix

##################################################

class GPSTimeException(Exception):
    pass

def cudate(string='now'):
    """Parse date/time string to UNIX timestamp with GNU coreutils date

    """
    cmd = ['date', '+%s.%N', '-d', string]
    try:
        ts = subprocess.check_output(cmd, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError:
        raise GPSTimeException("could not parse string '{}'".format(string))
    return float(ts)

def dt2ts(dt):
    """Return UNIX timestamp for datetime object.

    """
    try:
        dt = dt.astimezone(tzutc())
        tzero = datetime.fromtimestamp(0, tzutc())
    except ValueError:
        warnings.warn("GPS converstion requires timezone info.  Assuming local time...",
                      RuntimeWarning)
        dt = dt.replace(tzinfo=tzlocal())
        tzero = datetime.fromtimestamp(0, tzlocal())
    delta = dt - tzero
    return delta.total_seconds()

##################################################

class gpstime(datetime):
    """GPS-aware datetime class

    An extension of the datetime class, with the addition of methods
    for converting to/from GPS times:

    >>> from gpstime import gpstime
    >>> gt = gpstime.fromgps(1088442990)
    >>> gt.gps()
    1088442990.0
    >>> gt.strftime('%Y-%m-%d %H:%M:%S %Z')
    '2014-07-03 17:16:14 UTC'
    >>> gpstime.now().gps()
    1133737481.204008

    In addition a natural language parsing `parse` classmethod returns
    a gpstime object for a arbitrary time string:

    >>> gpstime.parse('2014-07-03 17:16:14 UTC').gps()
    1088442990.0
    >>> gpstime.parse('2 days ago').gps()
    1158440653.553765

    """
    def __new__(cls, *args):
        return datetime.__new__(cls, *args)

    @classmethod
    def fromdatetime(cls, datetime):
        """Return gpstime object from datetime object"""
        tzinfo = datetime.tzinfo
        if tzinfo is None:
            tzinfo = tzlocal()
        cls = gpstime(datetime.year, datetime.month, datetime.day,
                      datetime.hour, datetime.minute, datetime.second, datetime.microsecond,
                      tzinfo)
        return cls

    @classmethod
    def fromgps(cls, gps):
        """Return gpstime object corresponding to GPS time."""
        gt = cls.utcfromtimestamp(gps2unix(gps))
        return gt.replace(tzinfo=tzutc())

    @classmethod
    def parse(cls, string='now'):
        """Parse an arbitrary time string into a gpstime object.

        If string not specified 'now' is assumed.  Strings that can be
        cast to float are assumed to be GPS time.  Prepend '@' to
        specify a UNIX timestamp.

        This parse uses the natural lanuage parsing abilities of the
        GNU coreutils 'date' utility.  See "DATE STRING" in date(1)
        for information on possible date/time descriptions.

        """
        if not string:
            string = 'now'
        try:
            gps = float(string)
        except ValueError:
            gps = None
        if gps:
            gt = cls.fromgps(gps)
        elif string == 'now':
            gt = cls.now().replace(tzinfo=tzlocal())
        else:
            ts = cudate(string)
            gt = cls.fromtimestamp(ts).replace(tzinfo=tzlocal())
        return gt

    tconvert = parse

    def timestamp(self):
        """Return UNIX timestamp (seconds since epoch)."""
        return dt2ts(self)

    def gps(self):
        """Return GPS time as a float."""
        return float(unix2gps(self.timestamp()))

    def iso(self):
        """Return time in standard UTC ISO format"""
        return self.strftime(ISO_FORMAT)


def tconvert(string='now', form='%Y-%m-%d %H:%M:%S.%f %Z'):
    """Reimplementation of LIGO "tconvert" binary behavior

    Given a GPS time string, return the date/time string with the
    specified format.  Given a date/time string, return the GPS time.

    This just uses the gpstime.parse() method internally.

    """
    gt = gpstime.parse(string)
    try:
        float(string)
        return gt.strftime(form)
    except ValueError:
        return gt.gps()

##################################################
##################################################

if __name__ == '__main__':
    import argparse
    description = """GPS time conversion

Print local, UTC, and GPS time for the specified time string.
"""
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--version', action='store_true',
                        help="print version number and exit")
    zg = parser.add_mutually_exclusive_group()
    zg.add_argument('-l', '--local', action='store_const', dest='tz', const='local',
                    help="show only local time")
    zg.add_argument('-u', '--utc', action='store_const', dest='tz', const='utc',
                    help="show only UTC time (default)")
    zg.add_argument('-g', '--gps', action='store_const', dest='tz', const='gps',
                    help="show only GPS time")
    fg = parser.add_mutually_exclusive_group()
    fg.set_defaults(format='%Y-%m-%d %H:%M:%S.%f %Z')
    fg.add_argument('-i', '--iso', action='store_const', dest='format', const=ISO_FORMAT,
                    help="output time in ISO format")
    fg.add_argument('-f', '--format',
                    help="output time format (see strftime behavior: https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior)")
    parser.add_argument('time', metavar='TIME', nargs=argparse.REMAINDER, default='now',
                        help="time string, in any format (if none specified, output current time)")
    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit()

    def tzname(tz):
        return datetime.now(tz).tzname()

    try:
        gt = gpstime.parse(' '.join(args.time))
    except GPSTimeException as e:
        sys.exit("Error: {}".format(e))

    if not args.tz:
        ltz = tzlocal()
        utz = tzutc()
        print('{}: {}'.format(tzname(ltz), gt.astimezone(ltz).strftime(args.format)))
        print('{}: {}'.format('UTC', gt.astimezone(utz).strftime(args.format)))
        print('{}: {:.6f}'.format('GPS', gt.gps()))
    elif args.tz == 'gps':
        print('{:.6f}'.format(gt.gps()))
    else:
        if args.tz == 'local':
            tz = tzlocal()
        elif args.tz == 'utc':
            tz = tzutc()
        print('{}'.format(gt.astimezone(tz).strftime(args.format)))
