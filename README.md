GPS-aware datetime module

This package provides a gpstime module, which is a subclass of the
built-in datetime module with additional GPS access and conversion
methods.

Leap second data is automatically downloaded from the IETF database:

  https://www.ietf.org/timezones/data/leap-seconds.list

Leap data will be automatically updated as needed.

A command-line GPS data conversion utility that uses the gpstime
module is also included.  It is a rough work-alike to "tconvert".
