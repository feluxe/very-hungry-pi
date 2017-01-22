#!/usr/bin/env python3

# Copyright (C) 2016 Felix Meyer-Wolters
#
# This file is part of 'Very Hungry Pi' (vhpi) - An application to create backups.
#
# 'Very Hungry Pi' is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess as sub
import glob

from vhpi.logging import logger as log, ts_msg
from vhpi.utils import clean_path, check_path
import vhpi.processes as processes


def remove(_dir):
    """Remove Snapshot directory.
    Uses unix rm instead of shutil.rmtree for better performance.
    :param _dir:
    """
    log.debug(ts_msg(4, '  Remove snapshot: ' + _dir.split('/')[-1]))
    processes.rm = sub.check_output(['rm', '-rf', _dir])


def create_hardlinks(src, dst):
    """Create hard-links with unix cp tool."""
    log.debug(ts_msg(4, '  Create hardlinks: ' + src.split('/')[-1] + ' to ' + dst.split('/')[-1]))
    cmd = ['cp', '-al', src, dst]
    processes.cp = sub.Popen(cmd, shell=False,
                             stdin=sub.PIPE,
                             stdout=sub.PIPE,
                             stderr=sub.STDOUT,
                             universal_newlines=True)
    output = processes.cp.stdout.read()
    log.debug('\n    ' + output) if output else None
    processes.cp = None


def shift(interval, _dir):
    """Increase the dir num by one for selected snapshot type.
    :param interval: The interval of the snapshot that is being shifted.
    :param _dir: The directory which contains the snapshots.
    :return:
    """
    log.debug(ts_msg(4, '  Shift snapshot "' + interval + '" for ' + _dir))
    base_name = clean_path(_dir + '/' + interval + '.')
    for i in reversed(range(0, len(glob.glob(base_name + '*[0-9]')))):
        os.rename(base_name + str(i), base_name + str(i + 1))


def make(interval, src):
    """Create a new snapshot next to the src folder.
    :param interval: str. E.g.: 'hourly', 'daily', etc.
    :param src: The source dir. Usually the latest backup
    """
    log.debug(ts_msg(4, 'Start snapshot sequence: "' + interval + '" for: ' + src))
    parent_dir = os.path.dirname(src)
    snap_dir = clean_path(parent_dir + '/' + interval + '.0')
    remove(snap_dir + '.tmp')
    create_hardlinks(src, snap_dir + '.tmp')
    shift(interval, parent_dir) if os.path.exists(snap_dir) else None
    os.rename(snap_dir + '.tmp', snap_dir)
