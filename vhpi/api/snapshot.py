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
from glob import glob
from datetime import datetime
import subprocess as sub
import time
import re
from typing import Union, List, NamedTuple, Tuple, Dict
import vhpi.api.logging as log
from vhpi.utils import clean_path, load_yaml, save_yaml
from vhpi.api.types import BackupRoot, BackupLatest, SnapDir, SnapDirTmp, \
    Interval, KeepAmount, Job
import vhpi.constants as const


class Snap(NamedTuple):
    backup_root: BackupRoot
    src: BackupLatest
    dst_tmp: SnapDirTmp
    base_pattern: str
    interval: Interval
    keep_amount: KeepAmount


def _create_hardlinks(snap: Snap) -> None:
    """
    Create hard-links with unix cp tool.
    """
    log.debug(log.lvl1.ts_msg(
        f'Create hardlinks: {snap.src.split("/")[-1]} '
        f'-> {snap.dst_tmp.split("/")[-1]}'
    ))

    cmd = ['cp', '-al', snap.src, snap.dst_tmp]

    p = sub.Popen(
        cmd,
        shell=False,
        stdin=sub.PIPE,
        stdout=sub.PIPE,
        stderr=sub.STDOUT,
        universal_newlines=True
    )

    output = p.stdout.read()

    if output:
        log.debug('\n    ' + output)


def _split_num_from_path(
    path: str,
    interval: Interval,
) -> Tuple[str, int]:
    """"""
    last_bit: str = re.search(f'_{interval}\.[0-9]+', path).group()
    num = int(re.search(f'[0-9]+', last_bit).group())
    path_without_num: str = path[0:-len(str(num))]

    return path_without_num, num


def _shift(snap: Snap) -> None:
    """
    Increase the num in the dir by one for selected snapshot interval type.
    """
    log.debug(log.lvl1.ts_msg(
        f'Shift snapshot "{snap.interval}" in {snap.backup_root}'
    ))

    snaps_to_shift: List[str] = [
        item
        for item
        in glob(f'{snap.backup_root}/*')
        if f'_{snap.interval}.' in item
    ]

    for path in sorted(snaps_to_shift, reverse=True):
        path_wo_num, num = _split_num_from_path(path, snap.interval)
        search: str = f'{path_wo_num}{num}'
        replacement: str = f'{path_wo_num}{num+1}'

        new_path: str = re.sub(search, replacement, path)

        os.rename(
            src=path,
            dst=new_path
        )


def _get_deprecated_snaps(snap: Snap) -> Union[List[SnapDir], list]:
    """
    Get all deprecated snapshot dirs.
    Dirs that contain snapshots that are older than what the user wants to keep.
    The keep range is defined in the config yaml file.
    """
    keep_range: List[int] = range(0, snap.keep_amount)

    snaps_to_keep: Union[List[SnapDir], list] = [
        item
        for item
        in glob(f'{snap.backup_root}/*')
        if f'_{snap.interval}.' in item
           and _split_num_from_path(item, snap.interval)[1] in keep_range
    ]

    deprecated: Union[List[SnapDir], list] = [
        item
        for item
        in glob(f'{snap.backup_root}*')
        if f'_{snap.interval}.' in item
           and item not in snaps_to_keep
    ]

    return deprecated


def _rm_snap(dir_: Union[SnapDir, SnapDirTmp]) -> None:
    """
    Remove Snapshot directory.
    Uses unix rm instead of shutil.rmtree for better performance.
    """
    log.debug(log.lvl1.ts_msg(
        f'Remove deprecated snapshot: {os.path.basename(dir_)}'
    ))

    sub.check_call(['rm', '-rf', dir_])


def _rm_deprecated_snaps(snap: Snap) -> bool:
    """
    Delete deprecated snapshot directories.
    """
    deprecated: Union[List[SnapDir], list] = _get_deprecated_snaps(snap)

    for snap_dir in deprecated:
        try:
            _rm_snap(str(snap_dir))

        except sub.CalledProcessError as e:
            log.debug(e)
            log.error(
                f'    Error: Could not delete deprecated snapshot: {snap_dir}'
            )
            return False

    return True


def _update_timestamp(snap: Snap) -> None:
    """"""
    log.debug(log.lvl1.ts_msg(
        f'Update timestamp for "{snap.interval}".'
    ))

    timestamp_file: str = clean_path(
        f'{snap.backup_root}/{const.TIMESTAMP_FILE_NAME}'
    )
    timestamps: Dict[Interval, str] = load_yaml(timestamp_file) or {}

    timestamps[snap.interval] = time.strftime(const.TIMESTAMP_FORMAT)

    save_yaml(timestamps, timestamp_file)


def _init_snapshot(
    interval: Interval,
    job: Job,
) -> Snap:
    """"""
    # dst_base = clean_path(f'{job.backup_root}/{interval}_')
    # dst = f'{dst_base}0'
    # dst_tmp = f'{dst}_tmp'
    base_pattern = f'{job.backup_root}/[0-9]{4}-[0-9]{2}-[0-9]{2}' \
                   f'__[0-9]{2}:[0-9]{2}:[0-9]{2}__{interval}.'

    snap = Snap(
        backup_root=job.backup_root,
        src=clean_path(job.backup_latest),
        # dst_base=dst_base,
        # dst=dst,
        # dst_tmp=dst_tmp,
        dst_tmp=clean_path(f'{job.backup_root}/{interval}.tmp'),
        base_pattern=base_pattern,
        interval=interval,
        keep_amount=job.snapshots.get(interval),
    )
    return snap


def _make(
    interval: Interval,
    job: Job,
    timestamp: datetime,
) -> None:
    """
    Create a new snapshot from 'backup.latest'.
    """

    log.debug(log.lvl1.ts_msg(
        f'Start snapshot sequence: "{interval}" for: {job.backup_src}'
    ))

    snap = _init_snapshot(
        interval=interval,
        job=job,
    )

    # Remove leftovers.
    if os.path.exists(snap.dst_tmp):
        _rm_snap(snap.dst_tmp)

    _create_hardlinks(snap)

    _shift(snap)

    os.rename(
        src=snap.dst_tmp,
        dst=f'{snap.backup_root}/{timestamp.strftime("%Y-%m-%d__%H:%M:%S")}__'
            f'{snap.interval}.0'
    )

    _update_timestamp(snap)

    _rm_deprecated_snaps(snap)

    log.info(log.lvl1.ts_msg(f'Completed Snapshot: {snap.interval}'))
    log.debug('')


def routine(job: Job):
    timestamp = datetime.fromtimestamp(time.time())

    log.info(f'\n    [Snapshot Log]')
    log.debug('')

    for interval in job.due_snapshots:
        _make(
            interval=interval,
            job=job,
            timestamp=timestamp,
        )
