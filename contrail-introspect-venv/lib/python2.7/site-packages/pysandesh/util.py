#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# util
#

import datetime
import sys
import traceback
import collections

def UTCTimestampUsec():
    epoch = datetime.datetime.utcfromtimestamp(0)
    now = datetime.datetime.utcnow()
    delta = now-epoch
    return (delta.microseconds +
            (delta.seconds + delta.days * 24 * 3600) * 10**6)
# end UTCTimestampUsec


def UTCTimestampUsecToString(utc_usec):
    return datetime.datetime.fromtimestamp(
        utc_usec/1000000).strftime('%Y-%m-%d %H:%M:%S')
# end UTCTimestampUsecToString


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)
# end enum


def import_class(import_str):
    """Returns a class from a string including module and class."""
    mod_str, _sep, class_str = import_str.rpartition('.')
    __import__(mod_str)
    try:
        return getattr(sys.modules[mod_str], class_str)
    except AttributeError:
        raise ImportError('Class %s cannot be found (%s)' %
                          (class_str,
                           traceback.format_exception(*sys.exc_info())))

class deque(collections.deque):
    def __init__(self, iterable=(), maxlen=None):
        super(deque, self).__init__(iterable, maxlen)
        self._maxlen = maxlen
    @property
    def maxlen(self):
        return self._maxlen

# end class deque

