GPS-aware datetime module
=========================

This package provides a gpstime package, including a gpstime subclass
of the built-in datetime class with the addition of GPS access and
conversion methods.

Leap second data is provided by the ietf_leap_seconds module that
helps automatically maintain a local copy of the IETF leap second
list:

  https://www.ietf.org/timezones/data/leap-seconds.list

A command-line GPS data conversion utility that uses the gpstime
module is also included.  It is a rough work-alike to "tconvert".
