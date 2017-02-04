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
  <package_data_path>/leap-seconds.list

If all files are found to be out of date the module will throw a
warning to the user on import.  The data can be updated after import
by running the 'update_leapdata()' command.  This will download the
latest version from the above URL and store the updated file in the
user cache location.  System administrators wishing to maintain an
up-to-date version at the system cache location can run the following
from the command line:

  IETF_LEAPFILE=/var/cache/gpstime/leap-seconds.list \
  IETF_UPDATE=force \
  python -m gpstime

KNOWN BUGS: This module does not currently handle conversions of time
strings describing the actual leap second themselves, which are
usually represented as the 60th second of the minute during which the
leap second occurs.

"""

from __future__ import print_function
import os
import sys
import time
import requests
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
LEAPFILE_PAK = os.path.join(os.path.dirname(__file__), 'leap-seconds.list')
LEAPFILES = [LEAPFILE_USER, LEAPFILE_SYS, LEAPFILE_PAK]

LEAPDATA, LEAPDATA_EXPIRE = None, None

def __ietf_c_to_unix(c):
    """Convert time since century to time since UNIX epoch

    1900-01-01T00:00:00Z -> 1970-01-01T00:00:00Z

    """
    return int(c) - 2208988800

def __ietf_retrieve(path):
    """Download IETF leap second data to path

    """
    dd = os.path.dirname(path)
    if dd != '' and not os.path.exists(dd):
        os.makedirs(dd)
    r = requests.get(LEAPFILE_IETF)
    r.raise_for_status()
    with open(path+'.tmp', 'wb') as f:
        for c in r.iter_content():
            f.write(c)
    os.rename(path+'.tmp', path)

def __ietf_parse_leapfile(leapfile):
    """Parse leap second data from IETF leap-seconds.list file

    https://www.ietf.org/timezones/data/leap-seconds.list

    """
    data = []
    expire = 0
    if not os.path.isfile(leapfile):
        return data, expire
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

def is_leapdata_expired():
    return LEAPDATA_EXPIRE <= time.time()

def __load_leapdata(leapfile=os.getenv('IETF_LEAPFILE')):
    """Load IETF leap second data from user or system locations

    If `leapfile` is specified data will be loaded from that location
    instead.  Otherwise data will be loaded from the first of user or
    system path location that is not expired.

    If default behavior of this function can be modified via the
    IETF_LEAPFILE environment variable.

    """
    global LEAPDATA
    global LEAPDATA_EXPIRE
    leapfiles = LEAPFILES
    env_leapfile = os.getenv('IETF_LEAPFILE')
    if env_leapfile:
        leapfiles = [env_leapfile]
    for path in leapfiles:
        LEAPDATA, LEAPDATA_EXPIRE = __ietf_parse_leapfile(path)
        if not is_leapdata_expired():
            return
    # if we're here no non-expired leap data has been found
    warnings.warn("Leap second data is expired.  See update_leapdata() to update.",
                  RuntimeWarning, stacklevel=0)

#################
__load_leapdata()
#################

def update_leapdata(leapfile=os.getenv('IETF_LEAPFILE'),
                    update=os.getenv('IETF_UPDATE')):
    """Update user leap data cache file from online IETF bulletin

    If the leap data is expired, leap second data will be downloaded
    from the IETF and stored in the user data cache location:

       ~/.cache/gpstime/leap-seconds.list

    If a `leapfile` path is supplied that file will be updated
    instead.  If the `update` option is False or the strings 'FALSE'
    or 'NO' data will be loaded from the specified file without
    updating from the IETF.

    The default behavior of this function can be modified via the
    IETF_LEAPFILE and IETF_UPDATE environment variables.

    """
    if not leapfile:
        leapfile = LEAPFILE_USER
    if update is False or (update and update.upper() in ['FALSE', 'NO']):
        pass
    else:
        __ietf_retrieve(leapfile)
    __load_leapdata(leapfile)
    if is_leapdata_expired():
        raise RuntimeError("IETF leap data is expired or could not be updated.")

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
        # HACK: in python3, utcfromtimestamp() seems to floor instead
        # of round the microseconds.  this causes round trips to fail.
        # manually fix microseconds here to the rounded value instead.
        ms = int(round((gps - int(gps))*1000000))
        return gt.replace(microsecond=ms, tzinfo=tzutc())


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
        return unix2gps(self.timestamp())

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


def gpsnow():
    """Return current GPS time

    """
    return gpstime.utcnow().replace(tzinfo=tzutc()).gps()
