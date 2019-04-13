"""
    eve_mongoengine._compat
    ~~~~~~~~~~~~~~~~~~~~~~~

    Internal module for Python 2 backwards compatibility

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

# flake8: noqa

import sys

if sys.version_info[0] < 3:
    iteritems = lambda x: x.iteritems()
    iterkeys = lambda x: x.iterkeys()
    itervalues = lambda x: x.itervalues()
    u = lambda x: x.decode()
    b = lambda x: x
    next = lambda x: x.next()
    byte_to_chr = lambda x: x
    unichr = unichr
    xrange = xrange
    basestring = basestring
    unicode = unicode
    bytes = str
    long = long
else:
    iteritems = lambda x: iter(x.items())
    iterkeys = lambda x: iter(x.keys())
    itervalues = lambda x: iter(x.values())
    u = lambda x: x
    b = lambda x: x.encode("iso-8859-1") if not isinstance(x, bytes) else x
    next = next
    unichr = chr
    imap = map
    izip = zip
    xrange = range
    basestring = str
    unicode = str
    bytes = bytes
    long = int
