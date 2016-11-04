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
import subprocess
import glob

from vhpi.logging import logger as log, ts_msg
from vhpi.utils import clean_path, check_path
import vhpi.processes as processes


def remove(_dir):
    """Remove Snapshot directory. Uses unix rm instead of shutil.rmtree for better performance.
    :param _dir:
    """
    log.debug(ts_msg(2, 'Removing snapshot: ' + _dir.split('/')[-1]))
    try:
        processes.rm = subprocess.check_output(['rm', '-rf', _dir])
    except processes.rm.CalledProcessError as e:
        log.debug(e)
        log.critical('    Critical Error: Could not remove : ' + _dir)


def create_hardlinks(src, dest):
    """Create hard-links with unix cp tool."""
    if os.path.exists(dest):
        raise FileExistsError('Destination already exists.')
    log.debug(ts_msg(2, 'Making links from: ' + src.split('/')[-1] + ' to ' + dest.split('/')[-1]))
    processes.cp = subprocess.Popen(['cp', '-al', src, dest],
                                    shell=False,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    close_fds=True,
                                    universal_newlines=True)
    output = processes.cp.stdout.read()
    if output:
        log.debug(output)

    # handle cp exit codes
    processes.cp.communicate()
    return_code = processes.cp.wait()
    if return_code != 0:
        log.error('    Error: Could not create hardlinks for: ' + src)
    processes.cp = None


def shift(interval, _dir):
    """Increase the dir num by one for selected snapshot type.
    :param interval: The interval of the snapshot that is being shifted.
    :param _dir: The directory which contains the snapshots.
    :return:
    """
    log.debug(ts_msg(2, 'Shifting snapshots.'))
    base_name = clean_path(_dir + '/' + interval + '.')
    if check_path(base_name + '0') != 'dir':
        print(base_name + '0')
        log.debug(ts_msg(2, 'No Snapshot found. No shift necessary.'))
        return
    for i in reversed(range(0, len(glob.glob(base_name + '[0-9]')))):
        try:
            os.rename(base_name + str(i), base_name + str(i + 1))
        except OSError as e:
            log.debug(e)
            log.critical(4 * ' ' + 'Critical Error: Could not rename dir: '
                         + base_name + str(i)) + '==> ' + str(i + 1)


def make(interval, src):
    """Create a new snapshot next to the src folder.
    :param interval: str. E.g.: 'hourly', 'daily', etc.
    :param src: The source dir. Usually the latest backup
    """
    log.debug(ts_msg(2, 'Making snapshot: ' + interval + ' of ' + src))
    try:
        parent_dir = os.path.dirname(src)
        snap_dir = clean_path(parent_dir + '/' + interval + '.0')
        remove(snap_dir + '.tmp')
        create_hardlinks(src, snap_dir + '.tmp')
        shift(interval, parent_dir) if os.path.exists(snap_dir) else None
        os.rename(snap_dir + '.tmp', snap_dir)
    except Exception as e:
        raise RuntimeError(e)

