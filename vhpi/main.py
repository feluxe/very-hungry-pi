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


import fcntl
import sys
import time
import traceback

from vhpi.job import Job
from .lib import exit_main, load_yaml
from .logger import log
from .settings import Settings as S


# Check if another instance of the script is already running by using the 'flock' mechanism.
# If another instance is already running: exit app.
def check_lock(lockfile):
    try:
        lockfile = open(lockfile, 'w')
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.info('    Info: Another instance of this Script was executed, '
                 'but it was blocked successfully. ' +
                 time.strftime(S.timestamp_format))
        sys.exit()
    return lockfile


# load user config data into the Settings Object.
def init_settings():
    data = load_yaml(S.cfg_file)
    S.jobs_cfg = data['jobs_cfg']
    S.exclude_lib = data['app_cfg']['exclude_lib']
    S.intervals = data['app_cfg']['intervals']


# The main execution routine. It mainly loops over each backup job in the user config.
# For each backup job it creates an instance of 'Job' class.
def exec_app():
    lock = check_lock(S.lock_file)
    init_settings()
    # Loop through each job that is defined in cfg.
    for job_cfg in S.jobs_cfg:
        job = Job(job_cfg)  # Create job instance with job config data.
        job.init_time = time.time()  # Set initial timestamp
        if not job.check_readiness():  # Check if any snapshot due and machine online.
            continue
        log.job_in(job.src_ip, job.src, job.due_snapshots)
        job.health_check_routine()
        job.start_health_monitor()
        if job.alive and not job.exec_rsync():
            job.exit(2)
            continue
        if job.alive and not job.make_snapshots():
            job.exit(2)
            continue
        if job.alive:
            job.exit(0)
    exit_main()


def main():
    try:
        exec_app()
    except KeyboardInterrupt:
        log.error('Error: Backup aborted by user.')
        exit_main()
    except Exception:
        log.error('Error: An Exception was thrown.')
        log.error("-" * 60)
        log.error(traceback.format_exc())
        log.error("-" * 60)
        exit_main()


if __name__ == "__main__":
    main()
