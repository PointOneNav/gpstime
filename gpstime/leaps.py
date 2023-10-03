from functools import lru_cache
import os
import sys
import time
import calendar
import warnings

import appdirs

LEAPFILE_IANA = '/usr/share/zoneinfo/leapseconds'
LEAPFILE_IANA_USER = os.path.join(
    appdirs.user_cache_dir('gpstime'), 'leapseconds')

LEAPFILE_IERS = '/usr/share/zoneinfo/leap-seconds.list'
LEAPFILE_IERS_USER = os.path.join(
    appdirs.user_cache_dir('gpstime'), 'leap-seconds.list')


def ntp2unix(ts):
    """Convert NTP timestamp to UTC UNIX timestamp

    1900-01-01T00:00:00Z -> 1970-01-01T00:00:00Z

    """
    return int(ts) - 2208988800


def load_IANA(path):
    """Parse the `leapseconds` file format used by IANA.
    """
    data = []
    expires = 0
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line[:8] == '#expires':
                expires = int(line.split()[1])
            elif line[0] == '#':
                continue
            else:
                year, mon, day, ts, correction = line.split()[1:6]
                st = time.strptime(
                    '{} {} {} {}'.format(year, mon, day, ts),
                    '%Y %b %d %H:%M:%S',
                )
                # FIXME: do something with correction
                data.append(calendar.timegm(st))
    return data, expires


def load_IERS(path):
    """Parse the leap-seconds.list file format used by NIST, IERS, and IETF.
    """
    data = []
    expires = 0
    first = True
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            elif line[:2] == '#@':
                expires = ntp2unix(line.split()[1])
            elif line[0] == '#':
                continue
            else:
                # ignore the first entry since that doesn't
                # actually correspond to a leap second
                if first:
                    first = False
                    continue
                leap, offset = line.split()[:2]
                # FIXME: do something with offset
                data.append(ntp2unix(leap))
    return data, expires


def _download_http_file(url, path):
    """Download a file over HTTP or HTTPS.
    """
    import requests

    dd = os.path.dirname(path)
    if dd != '' and not os.path.exists(dd):
        os.makedirs(dd)

    r = requests.get(url)
    r.raise_for_status()
    with open(path, 'wb') as f:
        for c in r.iter_content():
            f.write(c)


def _download_ftp_file(url, path):
    import ftplib
    from urllib.parse import urlparse

    parts = urlparse(url)
    ftp = ftplib.FTP(host=parts.hostname)
    ftp.login()

    dd = os.path.dirname(path)
    if dd != '' and not os.path.exists(dd):
        os.makedirs(dd)

    with open(path, 'wb') as f:
        ftp.retrbinary("RETR %s" % parts.path, f.write)


def fetch_leapfile():
    # Candidate sources.
    #
    # Reference: https://kb.meinbergglobal.com/kb/time_sync/ntp/configuration/ntp_leap_second_file
    sources = [
        dict(download=_download_http_file, url='https://hpiers.obspm.fr/iers/bul/bulc/ntp/leap-seconds.list',
             load=load_IERS, path=LEAPFILE_IERS_USER),
        dict(download=_download_ftp_file, url='ftp://boulder.ftp.nist.gov/pub/time/leap-seconds.list',
             load=load_IERS, path=LEAPFILE_IERS_USER),
        dict(download=_download_ftp_file, url='ftp://ftp.nist.gov/pub/time/leap-seconds.list',
             load=load_IERS, path=LEAPFILE_IERS_USER),
        dict(download=_download_http_file, url='https://www.ietf.org/timezones/data/leap-seconds.list',
             load=load_IERS, path=LEAPFILE_IERS_USER),
        dict(download=_download_http_file, url='https://data.iana.org/time-zones/tzdb/leapseconds',
             load=load_IANA, path=LEAPFILE_IANA_USER),
    ]

    print("Updating local user leap data cache from known sources...", file=sys.stderr)
    for source in sources:
        # Download the file.
        try:
            temp_path = source['path'] + '.tmp'
            source['download'](url=source['url'], path=temp_path)
        except Exception as e:
            print('Unable to download leap seconds file from %s: %s' % (source['url'], str(e)), file=sys.stderr)
            continue

        # Load the file.
        try:
            data, expires = source['load'](temp_path)
            if len(data) == 0 or expires == 0:
                raise ValueError('Leap second data not found in file.')
        except Exception as e:
            print('Unable to load leap seconds file from %s: %s' % (source['url'], str(e)), file=sys.stderr)
            os.remove(temp_path)
            continue

        # Loaded successfully. Save the file.
        print('Successfully downloaded leap seconds file from %s.' % source['url'], file=sys.stderr)
        if os.path.exists(source['path']):
            os.remove(source['path'])
        os.rename(temp_path, source['path'])

        return data, expires

    raise RuntimeError('Unable to download leap second data file from available sources.')


class LeapData:
    """Leap second data.

    """
    _GPS0 = 315964800

    def __init__(self):
        """Initialize leap second data

        """
        # Load available data from disk.
        self._data = None
        self.expires = 0
        if os.path.exists(LEAPFILE_IANA):
            self._load(load_IANA, LEAPFILE_IANA)
        if not self.valid and os.path.exists(LEAPFILE_IERS):
            self._load(load_IERS, LEAPFILE_IERS)
        if not self.valid and os.path.exists(LEAPFILE_IANA_USER):
            self._load(load_IANA, LEAPFILE_IANA_USER)
        if not self.valid and os.path.exists(LEAPFILE_IERS_USER):
            self._load(load_IERS, LEAPFILE_IERS_USER)

        # Unable to load data, or data expired. Try to download an updated file.
        if not self.valid:
            if not self._data:
                print("Leap second data not available.", file=sys.stderr)
            elif self.expired:
                print("Leap second data is expired.", file=sys.stderr)

            # This will raise an exception if it cannot download or parse a file. Otherwise, it should always return
            # valid data.
            self._data, self.expires = fetch_leapfile()
            if self.expired:
                warnings.warn("Leap second data is expired.", RuntimeWarning)

    def _load(self, func, path):
        try:
            data, expires = func(path)
            if len(data) == 0 or expires == 0:
                raise ValueError('Leap second data not found in file.')
            else:
                self._data = data
                self.expires = expires
        except Exception as e:
            raise RuntimeError(f"Error loading leap file {path}: {str(e)}")

    @property
    def data(self):
        """Returns leap second data with times represented as UNIX.

        """
        if self.expired:
            warnings.warn("Leap second data is expired.", RuntimeWarning)
        return self._data

    @property
    def expired(self):
        """True if leap second data is expired

        """
        return self.expires <= time.time()

    @property
    def valid(self):
        """True if leap second data is available and not expired

        """
        return self._data and not self.expired

    def __iter__(self):
        for leap in self.data:
            yield leap

    @lru_cache(maxsize=None)
    def as_gps(self):
        """Returns leap second data with times represented as GPS.

        """
        leaps = [(leap - self._GPS0) for leap in self.data if leap >= self._GPS0]
        return [(leap + i) for i, leap in enumerate(leaps)]

    @lru_cache(maxsize=None)
    def as_unix(self, since_gps_epoch=False):
        """Returns leap second data with times represented as UNIX.

        If since_gps_epoch is set to True, only return leap second
        data since the GPS epoch (1980-01-06T00:00:00Z).

        """
        if since_gps_epoch:
            return [leap for leap in self.data if leap >= self._GPS0]
        else:
            return list(self.data)


LEAPDATA = LeapData()


if __name__ == '__main__':
    print("expires: {}".format(LEAPDATA.expires))
    for ls in LEAPDATA:
        print(ls)
