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


# This module contains the logic and routines that are needed to create a backup from a source
# directory.

import datetime
import subprocess
import glob
import threading
import os
import time

from .settings import Settings as S
from .logger import log
from .lib import clean_path, load_yaml, check_path, write_yaml, kill_processes, exit_main
from .processes import Processes


class Job(object):

    def __init__(self, _job_cfg):
        self.alive = True
        self.src_ip = _job_cfg['source_ip']
        self.src = _job_cfg['rsync_src']
        self.dest = _job_cfg['rsync_dest']
        self.rsync_options = _job_cfg['rsync_options']
        self.excludes = self.get_excludes(_job_cfg['excludes'],
                                          _job_cfg['exclude_lists'],
                                          S.exclude_lib)
        self.snapshots = _job_cfg['snapshots']
        self.timestamps = self.get_timestamps(self.dest, S.intervals)
        self.due_snapshots = self.get_due_snapshots(self.snapshots,
                                                    self.timestamps,
                                                    S.intervals)
        self.rsync_command = self.build_rsync_command(self.rsync_options,
                                                      self.excludes,
                                                      self.src,
                                                      self.dest)
        self.init_time = None
        self.validation_file = clean_path(self.src + "/" + S.validation_file)

    @staticmethod
    def get_timestamps(dest, intervals):
        timestamps = load_yaml(clean_path(dest + '/' + S.timestamp_file), True)
        if type(timestamps) is not dict:
            timestamps = {}
        for interval in intervals:
            if interval not in timestamps:
                timestamps.update({interval: 0})
        return timestamps

    # Get due Snapshots
    def get_due_snapshots(self, _snapshots, timestamps, intervals):
        due = [interval for interval in _snapshots
               if _snapshots[interval] and
               self.is_due(interval, intervals, timestamps[interval])]
        return due

    def check_validation_file(self):
        if not check_path(self.validation_file) == 'file':
            return False
        return True

    def check_dest(self):
        if not check_path(self.dest) == 'dir':
            return False
        return True

    @staticmethod
    def get_excludes(excludes, excl_lists, excl_lib):
        for _list in excl_lists:
            for item in excl_lib[_list]:
                excludes.append(item)
        return excludes

    # build rsync command for subprocess module.
    @staticmethod
    def build_rsync_command(options, excludes, src, dest):
        options = options.split()
        excludes = ['--exclude=' + item for item in excludes]
        src = clean_path(src)
        dest = clean_path(dest + '/backup.latest')
        return ['rsync'] + options + excludes + [src, dest]

    # check if machine is online.
    def is_machine_online(self):
        ping_command = ["ping", "-c", "1", self.src_ip]
        try:
            subprocess.check_output(ping_command)
            return True
        except subprocess.CalledProcessError:
            return False

    # Check if source is online repeatedly. If it goes offline exit program.
    def health_monitor(self):
        while self.alive:
            if not self.check_validation_file():
                log.critical('    Critical: Could not validate source via '
                          '"validation file"' + self.validation_file)
                self.exit(2)
            if not self.check_dest():
                log.critical('    Critical: Invalid Destination:' + self.dest + ': '
                         + time.strftime(S.timestamp_format))
                self.exit(2)
            if not self.is_machine_online():
                log.info('    Error: Source went offline: ' + time.strftime(S.timestamp_format))
                self.exit(2)
            time.sleep(60)

    # Start a watcher in a thread which checks if source machine is online, etc, each 60s.
    def start_health_monitor(self):
        health_monitor_thread = threading.Thread(target=self.health_monitor)
        health_monitor_thread.setDaemon(True)
        health_monitor_thread.start()

    # execute rsync command.
    def exec_rsync(self):
        log.debug_ts_msg('Start: rsync execution.')
        return_val = True
        try:
            log.info('    Executing: ' + ' '.join(self.rsync_command))
            Processes.rsync = subprocess.Popen(self.rsync_command,
                                               shell=False,
                                               stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT,
                                               close_fds=True,
                                               universal_newlines=True)
            output = Processes.rsync.stdout.read()
            if self.alive:
                log.debug('    ' + output.replace('\n', '\n    '))
                log.if_in_line('warning', 'rsync: ', output)
                log.if_in_line('warning', 'rsync error: ', output)
                log.if_in_line('info', 'bytes/sec', output)
                log.if_in_line('info', 'total size is ', output)
        except (subprocess.SubprocessError, subprocess.CalledProcessError) as e:
            if e.returncode and e.returncode != 23:
                log.warning('    Error: Unknown Rsync Exit Code')
                return_val = False
        Processes.rsync = None
        log.debug_ts_msg('End: rsync execution.\n') if self.alive else None
        return return_val

    @staticmethod
    # Determine if a snapshot is due.
    def is_due(_type, intervals, timestamp):
        if _type not in intervals:
            log.critical("    Critical: No time interval set for type: " + _type)
            exit_main()
        cycle_time = intervals[_type]
        if not isinstance(timestamp, str) or not timestamp:
            timestamp = '1970-01-01 00:00:00'
        _format = "%Y-%m-%d %H:%M:%S"
        timestamp = time.mktime(datetime.datetime.strptime(timestamp, _format).timetuple())
        time_now = int(time.time())
        if time_now - cycle_time >= timestamp:
            return True
        else:
            return False

    # Get all deprecated snapshot dirs.
    # Dirs that contain snapshots that are older than what the user wants to keep.
    # The keep range is defined in config.
    @staticmethod
    def get_deprecated_dirs(dest, snapshot, snapshots):
        deprecated = []
        base_dir = clean_path(dest + '/' + snapshot + ".")
        keep_range = range(snapshots[snapshot] - 2, -1, -1)
        active = [base_dir + str(num) for num in keep_range]
        active.append(base_dir + '0.tmp')
        deprecated.extend([_dir for _dir in glob.glob(base_dir + '*') if _dir not in active])
        return deprecated

    # Delete deprecated snapshot directories.
    def del_deprecated_snaps(self, dest, snapshot, snapshots):
        return_val = True
        deprecated = self.get_deprecated_dirs(dest, snapshot, snapshots)
        for _dir in deprecated:
            log.debug_ts_msg('  Deleting deprecated snapshot: ' + _dir)
            if check_path(_dir) == 'dir':
                try:
                    subprocess.check_output(['rm', '-rf', str(_dir)])
                except subprocess.CalledProcessError as e:
                    log.debug(e)
                    log.error('    Error: Could not delete deprecated snapshot' + _dir)
                    return_val = False
        return return_val

    # Increase the dir num by one for selected snapshot type.
    # Use the keep amount that is defined in config to find out how many dirs need to be changed.
    @staticmethod
    def shift_snaps(dest, snapshot, snapshots):
        log.debug_ts_msg('  Shifting snapshots.')
        output = True
        raw_path = clean_path(dest + '/' + snapshot + '.')
        for num in range(snapshots[snapshot] - 1, -1, -1):
            if check_path(raw_path + str(num)) == 'dir':
                try:
                    os.rename(raw_path + str(num), raw_path + str(num + 1))
                except OSError as e:
                    log.debug(e)
                    log.critical('    Critical Error: Could not rename dir: '
                                 + raw_path + str(num)) + '==> ' + str(num + 1)
                    output = False
        return output

    @staticmethod
    def update_timestamp(dest, snapshot, timestamps):
        log.debug_ts_msg('  Updating timestamp.')
        timestamps[snapshot] = time.strftime(S.timestamp_format)
        write_yaml(timestamps, clean_path(dest + '/' + S.timestamp_file))

    @staticmethod
    def remove_incomplete_snapshots(dest):
        output = True
        if check_path(dest) == 'dir':
            log.debug_ts_msg('  Removing old incomplete snapshot: ' + dest.split('/')[-1])
            try:
                subprocess.check_output(['rm', '-rf', dest])
            except subprocess.CalledProcessError as e:
                log.debug(e)
                log.critical('    Critical Error: Could not remove : ' + dest)
                output = False
        return output

    @staticmethod
    def make_hardlinks(src, dest):
        log.debug_ts_msg('  Making links from: ' + src.split('/')[-1] + ' to '
                         + dest.split('/')[-1])
        return_val = True
        try:
            Processes.cp = subprocess.Popen(['cp', '-al', src, dest],
                                            shell=False,
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            close_fds=True,
                                            universal_newlines=True)
            output = Processes.cp.stdout.read()
            if output:
                log.debug(output)
        except (subprocess.SubprocessError, subprocess.CalledProcessError) as e:
            log.debug(e)
            log.error('    Critical Error: Could not create hardlinks for: ' + src)
            return_val = False
        Processes.cp = None
        return return_val

    @staticmethod
    def rename_successful_snapshot(old):
        new = old.replace('.tmp', '')
        output = True
        log.debug_ts_msg('  Renaming snapshot from: '
                         '' + old.split('/')[-1] + ' to: ' + new.split('/')[-1])
        try:
            subprocess.check_output(['mv', old, new])
        except subprocess.CalledProcessError as e:
            log.debug(e)
            log.critical('    Critical Error: Could not rename dir from: ' + old + ' to: ' + new)
            output = False
        return output

    # Create hardlinks from 'backup.latest' to each queried
    #   snapshot dir. E.g. 'hourly.0', 'weekly.0', ...
    def make_snapshots(self):
        output = True
        for snapshot in self.due_snapshots:
            log.debug_ts_msg('Start: processing snapshot: ' + snapshot)
            source = clean_path(self.dest + '/backup.latest')
            snap_dest = clean_path(self.dest + '/' + snapshot + '.0.tmp')
            if not self.remove_incomplete_snapshots(snap_dest):
                continue
            if not self.make_hardlinks(source, snap_dest):
                continue
            if not self.del_deprecated_snaps(self.dest, snapshot, self.snapshots):
                continue
            if not self.shift_snaps(self.dest, snapshot, self.snapshots):
                continue
            if not self.rename_successful_snapshot(snap_dest):
                continue
            self.update_timestamp(self.dest, snapshot, self.timestamps)
            log.debug_ts_msg('  Successfully created snapshot: ' + snapshot)
        log.debug_ts_msg('End: processing snapshots.')
        log.info('')
        return output

    def check_readiness(self):
        output = True
        if not self.is_machine_online():
            log.skip_msg(False, self.due_snapshots, self.src_ip, self.src)
            output = False
        elif not self.due_snapshots:
            log.skip_msg(True, self.due_snapshots, self.src_ip, self.src)
            output = False
        return output

    def exit(self, code, msg=None, level=None):
        kill_processes()
        self.alive = False
        log.job_out(code, self.init_time)
