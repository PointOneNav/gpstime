"""IETF leap second

Download and parse IETF leap second list files

  https://www.ietf.org/timezones/data/leap-seconds.list

The assumed system cache location of the leap-seconds.list bulletin
file is given in the LEAPFILE_LOCAL variable.

"""

from __future__ import print_function
import os
import sys
import warnings
import traceback
from datetime import datetime
from dateutil.tz import tzutc, tzlocal

##################################################

LEAPFILE_IETF = 'https://www.ietf.org/timezones/data/leap-seconds.list'
LEAPFILE_SYSTEM = '/var/cache/ietf-leap-seconds/leap-seconds.list'
LEAPFILE_USER = os.path.expanduser('~/.cache/ietf-leap-seconds/leap-seconds.list')
LEAPFILES = [LEAPFILE_USER, LEAPFILE_SYSTEM]

ISO_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

class IETFParseError(Exception):
    pass

class IETFNoDataError(Exception):
    pass

def ntp2unix(ts):
    """Convert NTP timestamp to UTC UNIX timestamp

    1900-01-01T00:00:00Z -> 1970-01-01T00:00:00Z

    """
    return int(ts) - 2208988800

def ntp2dt(ts):
    """Convert NTP timestamp to UTC datetime object

    """
    return datetime.fromtimestamp(ntp2unix(ts)).replace(tzinfo=tzlocal()).astimezone(tzutc())

class IETFLeapData(object):
    """IETF leap second data object"""
    def __init__(self, path):
        """load IETF leap second list data from file

        Raises IETFParseError if the file could not be parsed or the
        data is invalid.

        """
        self.data = ()
        self.expire = 0
        with open(path, 'r') as f:
            try:
                for line in f:
                    if line[:2] == '#@':
                        self.expire = int(line.split()[1])
                    elif line[0] == '#':
                        pass
                    else:
                        sl = line.split()
                        ntp = int(sl[0])
                        offset = int(sl[1])
                        self.data += ((ntp, offset),)
            except:
                raise IETFParseError('Syntax parse error.  Traceback:\n{}'.format(traceback.format_exc()))
        if not self.expire:
            raise IETFParseError("Expiration could not be parsed from file.")
        if not self.data:
            raise IETFParseError("No leap second data found in file.")
        # FIXME: check hash ('#h')
        self.path = os.path.abspath(path)

    @property
    def expired(self):
        """True if leap second data is expired"""
        return ntp2dt(self.expire) <= datetime.utcnow().replace(tzinfo=tzlocal())

    def _warn_expired(self):
        if self.expired:
            warnings.warn("Leap second data is expired.", RuntimeWarning)

    def __iter__(self):
        """generator of leap seconds as NTP timestamps"""
        for leap in self.data:
            yield leap[0]

    def as_unix(self):
        """generator of leap seconds as UTC UNIX timestamps"""
        for leap in self:
            yield ntp2unix(leap)

    def as_datetime(self):
        """generator of leap seconds as datetime objects"""
        for leap in self:
            yield ntp2dt(leap)

def fetch_leapfile(path):
    """Download IETF leap second data to path

    Downloaded file will be parsed/validated before writing to path.

    """
    import requests
    dd = os.path.dirname(path)
    if dd != '' and not os.path.exists(dd):
        os.makedirs(dd)
    r = requests.get(LEAPFILE_IETF)
    r.raise_for_status()
    tmp = path+'.tmp'
    with open(tmp, 'wb') as f:
        for c in r.iter_content():
            f.write(c)
    ld = IETFLeapData(tmp)
    if ld.expired:
        warnings.warn("IETF leap data is expired.")
    os.rename(tmp, path)

def load_leapdata(leapfile=os.getenv('IETF_LEAPFILE'),
                  update=True, notify=False):
    """Load and return IETF leap second data

    Find valid local leap second list data and return an IETFLeapData
    object.  If a `leapfile` argument is provided or the IETF_LEAPFILE
    environment variable is set the specified file will be used.
    Otherwise the specified the user cache location (LEAPFILE_USER)
    and system cache location (LEAPFILE_SYSTEM) will be examined.  If
    no valid files are found and the `update` flag is True the user
    cache file will updated if expired.

    """
    if leapfile:
        ld = IETFLeapData(leapfile)
        ld._warn_expired()
        return ld

    ld = None
    for lf in LEAPFILES:
        try:
            ld = IETFLeapData(lf)
        except IOError:
            continue
        if not ld.expired:
            break
    if not ld and not update:
        raise IETFNoDataError("No leap data files found.  Run with 'update=True' to download user cache.")
    elif (not ld or (ld and ld.expired)) and update:
        if notify:
            print("updating user leap second data from IETF...", file=sys.stderr)
        leapfile = LEAPFILE_USER
        fetch_leapfile(leapfile)
        ld = IETFLeapData(leapfile)
    ld._warn_expired()
    return ld

##################################################

def main():
    import sys
    import argparse

    description = """IETF leap second list

If no path is specified the system leap-seconds.list file will be
used.  By default all leap second times are returned as NTP
timestamps.  A return code of 10 indicates that the leap second list
is expired.

The IETF_LEAPFILE environment variable can be used to define a default
leap second list file path.
"""
    epilog = """For more information see the IETF web site:

  {}
""".format(LEAPFILE_IETF)
    parser = argparse.ArgumentParser(description=description,
                                     epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-p', '--print-path', action='store_true',
                   help="print leap data file path")
    g.add_argument('-e', '--print-expire', action='store_true',
                   help="print leap data expiration in ISO format")
    g.add_argument('-s', '--unix', action='store_true',
                   help="print leap seconds as UTC UNIX timestamp")
    g.add_argument('-i', '--iso', action='store_const', dest='format', const=ISO_FORMAT,
                   help="print leap seconds in ISO format")
    g.add_argument('-f', '--format',
                   help="specify leap seconds time format (see python strftime)")
    g.add_argument('-u', '--update', metavar='PATH',
                   help="update IETF leap second list file at specified path")

    args = parser.parse_args()

    if args.update:
        fetch_leapfile(args.update)
        ld = IETFLeapData(args.update)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            ld = load_leapdata(notify=True)

    if ld.expired:
        print("WARNING: Leap second data is expired.", file=sys.stderr)

    if args.print_path:
        print(ld.path)
    elif args.print_expire:
        print(ntp2dt(ld.expire).strftime(ISO_FORMAT))
    elif args.update:
        pass
    else:
        if args.unix:
            for ts in ld.as_unix():
                print(ts)
        elif args.format:
            for dt in ld.as_datetime():
                print(dt.strftime(args.format))
        else:
            for ts in ld:
                print(ts)
    if ld.expired:
        sys.exit(10)

if __name__ == '__main__':
    main()
