#!/usr/bin/env python

import unittest
import time
import datetime
from dateutil.tz import tzutc, tzlocal

import gpstime

##################################################

class TestGPStime(unittest.TestCase):
    def test_conversion(self):
        self.assertEqual(gpstime.gps2unix(1133585676), 1449550459)
        self.assertEqual(gpstime.unix2gps(1449550459), 1133585676)

    def test_conversion_past(self):
        self.assertEqual(gpstime.gps2unix(123456789), 439421586)
        self.assertEqual(gpstime.unix2gps(439421586), 123456789)

    def test_conversion_onleap(self):
        self.assertEqual(gpstime.gps2unix(425520006), 741484798)
        self.assertEqual(gpstime.gps2unix(425520007), 741484799)
        self.assertEqual(gpstime.gps2unix(425520008), 741484799)
        self.assertEqual(gpstime.gps2unix(425520009), 741484800)
        self.assertEqual(gpstime.unix2gps(741484798), 425520006)
        self.assertEqual(gpstime.unix2gps(741484799), 425520007)
        self.assertEqual(gpstime.unix2gps(741484800), 425520009)

    def test_gpstime_new(self):
        self.assertEqual(gpstime.gpstime(2015, 12, 8, 4, 54, 19, 0, tzutc()).gps(),
                         1133585676.0)

    def test_gpstime_from_datetime(self):
        dt = datetime.datetime(2015, 12, 8, 4, 54, 19, 0, tzutc())
        self.assertEqual(gpstime.gpstime.from_datetime(dt).gps(),
                         1133585676.0)

    def test_gpstime_parse_utc(self):
        self.assertEqual(gpstime.gpstime.parse('Dec 08 2015 04:54:19 UTC').gps(),
                         1133585676.0)

    def test_gpstime_parse_local(self):
        self.assertEqual(gpstime.gpstime.parse('Dec 08 2015 04:54:19 PDT').gps(),
                         1133614476.0)

    def test_gpstime_parse_gps(self):
        self.assertEqual(gpstime.gpstime.parse(1133585676).iso(),
                         '2015-12-08T04:54:19.000000Z')

    def test_gpstime_from_gps(self):
        self.assertEqual(gpstime.gpstime.from_gps(1133585676).iso(),
                         '2015-12-08T04:54:19.000000Z')

    @unittest.expectedFailure
    def test_gpstime_parse_leap(self):
        self.assertEqual(gpstime.gpstime.parse('Jun 30 1993 23:59:60 UTC').gps(),
                         425520008)

    @unittest.expectedFailure
    def test_gpstime_parse_gps_leap(self):
        self.assertEqual(gpstime.gpstime.parse(425520008).iso(),
                         '1993-06-30T23:59:60.000000Z')

##################################################

if __name__ == '__main__':
    unittest.main(verbosity=5, failfast=False, buffer=True)
