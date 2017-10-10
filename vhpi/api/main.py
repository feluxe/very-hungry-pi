# Copyright (C) 2016-2017 Felix Meyer-Wolters
#
# This file is part of 'Very Hungry Pi' (vhpi) - An application to create backups.
#
# 'Very Hungry Pi' is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License v3 as published by
# the Free Software Foundation.
#
# 'Very Hungry Pi' is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with 'Very Hungry Pi'.  If not, see <http://www.gnu.org/licenses/>.

import sys
import fcntl
import os
import time
from datetime import datetime
from typing import Dict
from vhpi.utils import load_yaml, clean_path
from vhpi.api import backup, snapshot, health
from vhpi.api.types import Job, Settings
from vhpi.api.types import BackupRoot, Interval, KeepAmount, IntervalDuration
import vhpi.constants as const
from vhpi.api.logging import skip_msg, job_start_msg, ts_msg, job_out_msg
import vhpi.api.logging as log


def check_lock(lockfile):
    """
    Check if another instance of the script is already running by using the
    'flock' mechanism. If another instance is already running: exit app.
    """
    try:
        lockfile = open(lockfile, 'w')
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

    except BlockingIOError:
        log.debug(ts_msg(4, 'Info: Another instance of vhpi was executed and '
                            'blocked successfully.'))
        sys.exit(0)
    return lockfile


def init_job(
    job_cfg: dict,
    settings: Settings,
    init_time: int,
):
    """"""
    timestamps = load_timestamps(
        backup_root=job_cfg.get('rsync_dst'),
        intervals=settings.intervals
    )

    due_snapshots = get_due_snapshots(
        timestamps=timestamps,
        snapshots=job_cfg.get('snapshots'),
        intervals=settings.intervals
    )

    return Job(
        init_time=init_time,
        name=job_cfg.get('name'),
        source_ip=job_cfg.get('source_ip'),
        backup_src=job_cfg.get('rsync_src'),
        backup_root=job_cfg.get('rsync_dst'),
        backup_latest=f'{job_cfg.get("rsync_dst")}/backup.latest',
        rsync_options=job_cfg.get('rsync_options'),
        exclude_lists=job_cfg.get('exclude_lists'),
        excludes=job_cfg.get('excludes'),
        snapshots=job_cfg.get('snapshots'),
        timestamps=timestamps,
        due_snapshots=due_snapshots,
    )


def is_snap_due(
    interval: Interval,
    intervals: Dict[Interval, int],
    timestamp: str
) -> bool:
    """"""
    if interval not in intervals:
        log.critical(f"    Critical: No time interval set for type: {interval}")
        sys.exit(1)

    if not timestamp or not isinstance(timestamp, str):
        timestamp = '1970-01-02 00:00:00'

    interval_duration: int = intervals[interval]
    format_ = const.TIMESTAMP_FORMAT
    timestamp = datetime.strptime(timestamp, format_).timetuple()
    timestamp = int(time.mktime(timestamp))
    time_now = int(time.time())

    if time_now - timestamp >= interval_duration:
        return True

    else:
        return False


def load_timestamps(
    backup_root: BackupRoot,
    intervals: Dict[Interval, IntervalDuration]
):
    """"""
    timestamp_file = clean_path(f'{backup_root}/{const.TIMESTAMP_FILE_NAME}')

    # Create empty timestamps file.
    if not os.path.isfile(timestamp_file):
        open(timestamp_file, 'a').close()

    timestamps = load_yaml(timestamp_file, True) or {}

    for interval in intervals:
        if not timestamps.get(interval):
            timestamps.update({interval: 0})

    return timestamps


def get_due_snapshots(
    timestamps: Dict[Interval, str],
    snapshots: Dict[Interval, KeepAmount],
    intervals: Dict[Interval, IntervalDuration],
):
    """
    @timestamps: Last snapshot completions.
    """
    return [
        interval
        for interval
        in snapshots
        if snapshots.get(interval)
           and is_snap_due(interval, intervals, timestamps[interval])
    ]


def duty_check_routine(job: Job):
    """"""
    if not job.due_snapshots:
        log.info(skip_msg(
            online=True,
            due_jobs=job.due_snapshots,
            ip=job.source_ip,
            path=job.backup_src
        ))
        return False

    if not health.is_machine_online(source_ip=job.source_ip):
        log.info(skip_msg(
            online=False,
            due_jobs=job.due_snapshots,
            ip=job.source_ip,
            path=job.backup_src
        ))
        return False

    return True


def run_job(
    job_cfg: dict,
    settings: Settings,
):
    """"""
    init_time: int = time.time()

    if not health.initial_job_validation_routine(
        job_cfg=job_cfg,
        init_time=init_time,
    ):
        return

    job: Job = init_job(
        job_cfg=job_cfg,
        settings=settings,
        init_time=init_time,
    )

    if not duty_check_routine(job):
        return

    log.info(job_start_msg(
        ip=job.source_ip,
        src=job.backup_src,
        due_snapshots=job.due_snapshots
    ))

    if not backup.exec_rsync(
        job=job,
        settings=settings,
    ):
        return

    if not snapshot.routine(
        job=job
    ):
        return

    log.job_out_msg(
        completed=True,
        timestamp=time.time(),
    )


def run(cfg: dict):
    """"""
    lock = check_lock(f'{const.APP_CFG_DIR}/lock')

    health.initial_app_validation_routine(cfg)

    settings = Settings(
        exclude_lib=cfg.get('app_cfg').get('exclude_lib'),
        intervals=cfg.get('app_cfg').get('intervals'),
    )

    for job_cfg in cfg['jobs']:
        run_job(job_cfg, settings)
