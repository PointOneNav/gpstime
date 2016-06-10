#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import time
import urllib
import datetime
import dateutil
import dateutil.parser
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
                #print('%s -> %s, %s %s %s' % (sl[0], unix, offset, datetime.datetime.fromtimestamp(unix, tzutc()), sl[3:]))
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

def unix2gps(unix):
    gps = unix - GPS0
    for leap, offset in LEAPDATA:
        if unix < leap:
            break
        gps += 1
    return gps

def gps2unix(gps):
    unix = gps + GPS0
    for leap, offset in LEAPDATA:
        if unix < leap:
            break
        unix -= 1
    return unix

##################################################

class gpstime(datetime.datetime):
    """GPS-aware datetime object

    An extension of the datetime.datetime object, with the addition of
    a two methods for converting from/to GPS times:

    >>> from gpstime import gpstime
    >>> gt = gpstime.fromgps(1088442990)
    >>> gt.gps()
    1088442990.0
    >>> gt.strftime('%Y-%m-%d %H:%M:%S')
    '2014-07-03 17:16:14'
    >>> gpstime.now().gps()
    1133737481.204008
    >>> gpstime.parse('2014-07-03 17:16:14 UTC').gps()
    1088442990.0

    This interface uses the IETF leap second bulletin:

    https://www.ietf.org/timezones/data/leap-seconds.list

    """
    def __new__(cls, *args):
        return datetime.datetime.__new__(cls, *args)

    @classmethod
    def fromdatetime(cls, datetime):
        """Return gpstime object from datetime object"""
        tzinfo = datetime.tzinfo
        if tzinfo is None:
            tzinfo = dateutil.tz.tzlocal()
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

        If string not specified NOW is assumed.

        """
        if not string:
            string = 'now'
        # assume GPS time if string can be converted to a float
        try:
            gps = float(string)
        except ValueError:
            if string == 'now':
                dt = datetime.datetime.now()
            else:
                dt = dateutil.parser.parse(string)
            gt = cls.fromdatetime(dt)
        else:
            gt = cls.fromgps(gps)
        return gt

    def timestamp(self):
        """Return UNIX time (seconds since epoch)."""
        delta = self - datetime.datetime.fromtimestamp(0, self.tzinfo)
        try:
            return delta.total_seconds()
        except AttributeError:
            # FIXME: this is for python2.6 compatibility
            return (delta.days * 24 * 3600) + delta.seconds + (delta.microseconds * 1e-6)

    def gps(self):
        """Return GPS time as a float."""
        return float(unix2gps(self.timestamp()))

    def iso(self):
        """Return time as proper ISO format UTC"""
        return self.strftime(ISO_FORMAT)

##################################################
##################################################

if __name__ == '__main__':
    import argparse
    description = '''GPS time conversion

Print local, UTC, and GPS time for specified time string.
'''
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
    fg.add_argument('-f', '--format',
                    help="output time format (see strftime behavior: https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior)")
    fg.add_argument('-i', '--iso', action='store_const', dest='format', const=ISO_FORMAT,
                    help="output time in ISO format")
    parser.add_argument('time', nargs=argparse.REMAINDER,
                        help="time string, in any format (if none specified, output time NOW)")
    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit()

    def tzname(tz):
        return datetime.datetime.now(tz).tzname()

    gt = gpstime.parse(' '.join(args.time))

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
