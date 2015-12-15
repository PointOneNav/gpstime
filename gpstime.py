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
#import pytz
import subprocess

##################################################

ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

##################################################

# UNIX time for GPS 0 (1980-01-06T00:00:00Z)
GPS0 = 315964800
USER_LEAPDATA = os.path.expanduser('~/.cache/gpstime/leap-seconds.list')
SYS_LEAPDATA = '/var/cache/gpstime/leap-seconds.list'
IETF_LEAPDATA = 'https://www.ietf.org/timezones/data/leap-seconds.list'

def __ietf_c_to_unix(c):
    '''Convert time since century to time since UNIX epoch

    1900-01-01T00:00:00Z -> 1970-01-01T00:00:00Z
    '''
    return int(c) - 2208988800

def __ietf_update_file(path):
    '''Download IETF leap second data to path

    '''
    print('updating leap second data from IETF...', file=sys.stderr)
    urllib.urlretrieve(IETF_LEAPDATA, path+'.tmp')
    os.rename(path+'.tmp', path)

def __ietf_get_uptodate():
    '''Get up-to-date IETF leap second data

    Looks in user and system cache locations for IETF
    leap-seconds.list, then updates the user cache if no files could
    be found or were all expired.

    '''
    # first look in user and system locations
    for path in [USER_LEAPDATA, SYS_LEAPDATA]:
        if os.path.isfile(path):
            data, expire = __ietf_parse_leapdata(path)
            if expire >= time.time():
                #print(path, file=sys.stderr)
                return data
    # all files either don't exist or are expired, so update user data
    # from IETF
    try:
        dd = os.path.dirname(USER_LEAPDATA)
        if not os.path.exists(dd):
            os.makedirs(dd)
        __ietf_update_file(USER_LEAPDATA)
    except:
        pass
    data, expire = __ietf_parse_leapdata(USER_LEAPDATA)
    if expire < time.time():
        print('WARNING: leap second data is expired, and could not be updated from the IETF', file=sys.stderr)
    return data

def __ietf_parse_leapdata(leapdata):
    '''Parse leap second data from IETF leap-seconds.list file

    https://www.ietf.org/timezones/data/leap-seconds.list
    '''
    data = []
    with open(leapdata) as f:
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
    >>> gt = gpstime.from_gps(1088442990)
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
    def from_datetime(cls, datetime):
        """Return gpstime object from datetime object"""
        tzinfo = datetime.tzinfo
        if tzinfo is None:
            tzinfo = dateutil.tz.tzlocal()
        cls = gpstime(datetime.year, datetime.month, datetime.day,
                      datetime.hour, datetime.minute, datetime.second, datetime.microsecond,
                      tzinfo)
        return cls

    @classmethod
    def from_gps(cls, gps):
        """Return gpstime object corresponding to GPS time."""
        gt = cls.utcfromtimestamp(gps2unix(gps))
        return gt.replace(tzinfo=tzutc())

    @classmethod
    def parse(cls, string):
        """Parse an arbitrary time string into a gpstime object."""
        # assume GPS time if string can be converted to a float
        try:
            gps = float(string)
        except ValueError:
            gps = None
        if gps:
            gt = cls.from_gps(gps)
        else:
            if string == 'now':
                dt = datetime.datetime.now()
            else:
                dt = dateutil.parser.parse(string)
            gt = cls.from_datetime(dt)
        return gt

    def timestamp(self):
        """Return UNIX time (seconds since epoch)."""
        return (self - datetime.datetime.fromtimestamp(0, self.tzinfo)).total_seconds()

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
    parser.add_argument('-i', '--iso', action='store_true',
                        help="output times in ISO format")
    parser.add_argument('time', nargs=argparse.REMAINDER,
                        help="time string, in any format (if none specified, output time NOW)")
    args = parser.parse_args()

    def tzname(tz):
        return datetime.datetime.now(tz).tzname()

    ltz = tzlocal()

    if len(args.time) == 0:
        gt = gpstime.utcnow()
        gt = gt.replace(tzinfo=tzutc())
    else:
        gt = gpstime.parse(' '.join(args.time))

    if args.iso:
        form = ISO_FORMAT
    else:
        form = '%Y-%m-%d %H:%M:%S.%f'

    print('%s: %s'   % (tzname(ltz), gt.astimezone(ltz).strftime(form)))
    print('%s: %s'   % ('UTC', gt.astimezone(tzutc()).strftime(form)))
    print('%s: %.6f' % ('GPS', gt.gps()))
