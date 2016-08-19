#!/usr/bin/env python3

# This module contains Processes that are spawn by the application.
# Any Process that is spawn should sit on a variable in this module, that way each process is
# globally available.

class Processes(object):
    rsync = None
    cp = None
