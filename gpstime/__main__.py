from __future__ import print_function
import sys
import argparse
from dateutil.tz import tzutc, tzlocal
import ietf_leap_seconds
from . import ISO_FORMAT, gpstime, GPSTimeException

def tzname(tz):
    return gpstime.now(tz).tzname()

def main():
    description = """GPS time conversion

Print local, UTC, and GPS time for the specified time string.
"""
    epilog = """See the python datetime module for time formating options:
https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
"""
    parser = argparse.ArgumentParser(description=description,
                                     epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--version', action='store_true',
                        help="print version number and exit")
    zg = parser.add_mutually_exclusive_group()
    zg.add_argument('-l', '--local', action='store_const', dest='tz', const='local',
                    help="print only local time")
    zg.add_argument('-u', '--utc', action='store_const', dest='tz', const='utc',
                    help="print only UTC time (default)")
    zg.add_argument('-g', '--gps', action='store_const', dest='tz', const='gps',
                    help="print only GPS time")
    fg = parser.add_mutually_exclusive_group()
    fg.set_defaults(format='%Y-%m-%d %H:%M:%S.%f %Z')
    fg.add_argument('-i', '--iso', action='store_const', dest='format', const=ISO_FORMAT,
                    help="use ISO time format")
    fg.add_argument('-f', '--format',
                    help="specify time format (see below)")
    parser.add_argument('time', metavar='TIME', nargs=argparse.REMAINDER, default='now',
                        help="time string in any format (including GPS), or current time if not specified")
    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit()

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

##################################################

if __name__ == '__main__':
    main()
