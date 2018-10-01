# Copyright (C) 2016-2017 Felix Meyer-Wolters
#
# This file is part of 'Very Hungry Pi' (vhpi) - An application to create
# backups.
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

import os
import sys
import time
from datetime import datetime
from typing import Dict, List
from vhpi.api import validate, backup, snapshot
from vhpi.utils import load_yaml, clean_path
import vhpi.constants as const
import vhpi.api.logging as log
from vhpi.api.types import BackupRoot, Interval, KeepAmount, IntervalDuration, \
    Job, Settings


def _initial_job_validation_routine(
    job_cfg: dict,
) -> bool:
    """
    These checks are to validate the user config for each job.
    You may only use lvl0 log output here.
    """
    backup_src: str = job_cfg.get('rsync_src')
    backup_dst: str = job_cfg.get('rsync_dst')

    if not type(backup_src) == str:
        log.lvl0.cfg_type_error('rsync_src', 'string')
        return False

    if not type(backup_dst) == str:
        log.lvl0.cfg_type_error('rsync_dst', 'string')
        return False

    if not backup_src[0] in ['/']:
        log.lvl0.cfg_no_absolute_path_error('rsync_src')
        return False

    if not backup_dst[0] in ['/']:
        log.lvl0.cfg_no_absolute_path_error('rsync_dst')
        return False

    if not validate.backup_dst_is_dir(backup_dst):
        log.lvl0.cfg_dst_not_exists_error(backup_dst)
        return False

    return True


def _is_snap_due(
    interval: Interval,
    intervals: Dict[Interval, int],
    timestamp: str
) -> bool:
    """"""
    if interval not in intervals:
        log.critical(f"    Critical: No time interval set for type: {interval}")
        sys.exit(1)

    if not timestamp or not isinstance(timestamp, str):
        timestamp: str = '1970-01-02 00:00:00'

    interval_duration: int = intervals[interval]
    format_: str = const.TIMESTAMP_FORMAT
    timestamp: tuple = datetime.strptime(timestamp, format_).timetuple()
    timestamp = int(time.mktime(timestamp))
    time_now = int(time.time())

    if time_now - timestamp >= interval_duration:
        return True

    else:
        return False


def _load_timestamps(
    backup_root: BackupRoot,
    intervals: Dict[Interval, IntervalDuration]
) -> Dict[Interval, str]:
    """"""
    timestamp_file = clean_path(f'{backup_root}/{const.TIMESTAMP_FILE_NAME}')

    # Create empty timestamps file if necessary.
    if not os.path.isfile(timestamp_file):
        open(timestamp_file, 'a').close()

    timestamps: Dict[Interval, str] = load_yaml(timestamp_file) or {}

    for interval in intervals:
        if not timestamps.get(interval):
            timestamps.update({interval: '1970-01-02 00:00:00'})

    return timestamps


def _get_due_snapshots(
    timestamps: Dict[Interval, str],
    snapshots: Dict[Interval, KeepAmount],
    intervals: Dict[Interval, IntervalDuration],
) -> List[Interval]:
    """
    @timestamps: Last snapshot completions.
    """
    return [
        interval
        for interval
        in snapshots
        if snapshots.get(interval)
           and _is_snap_due(interval, intervals, timestamps[interval])
    ]


def _init_job(
    job_cfg: dict,
    settings: Settings,
    init_time: float,
) -> Job:
    """"""
    timestamps: Dict[Interval, str] = _load_timestamps(
        backup_root=job_cfg.get('rsync_dst'),
        intervals=settings.intervals
    )

    due_snapshots: List[Interval] = _get_due_snapshots(
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


def _duty_check_routine(job: Job) -> bool:
    """"""
    if not job.due_snapshots:
        log.lvl0.skip_info(
            online=True,
            due_jobs=job.due_snapshots,
            ip=job.source_ip,
            path=job.backup_src
        )
        return False

    if not validate.is_machine_online(source_ip=job.source_ip):
        log.lvl0.skip_info(
            online=False,
            due_jobs=job.due_snapshots,
            ip=job.source_ip,
            path=job.backup_src
        )
        return False

    return True


def run(
    job_cfg: dict,
    settings: Settings,
) -> None:
    """"""
    init_time: float = time.time()

    if not _initial_job_validation_routine(
        job_cfg=job_cfg,
    ):
        return

    job: Job = _init_job(
        job_cfg=job_cfg,
        settings=settings,
        init_time=init_time,
    )

    if not _duty_check_routine(job):
        return

    log.lvl0.job_start_info(
        ip=job.source_ip,
        src=job.backup_src,
        due_snapshots=job.due_snapshots
    )

    if not backup.exec_rsync(
        job=job,
        settings=settings,
    ):
        return

    snapshot.routine(
        job=job
    )

    log.lvl0.job_out_info(
        completed=True,
        init_time=init_time,
    )
