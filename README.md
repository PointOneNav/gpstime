GPS-aware datetime module
=========================

This package provides a gpstime package, including a gpstime subclass
of the built-in datetime class with the addition of GPS access and
conversion methods.

Leap second data, necessary for GPS time conversion, is expected to be
provided by the core libc Time Zone Database tzdata.  If for some
reason the tzdata leapsecond file is not available, a local cache of
the IETF leap second record will be maintained:

  https://www.ietf.org/timezones/data/leap-seconds.list

A command-line GPS data conversion utility that uses the gpstime
module is also included.  It is a rough work-alike to "tconvert".
