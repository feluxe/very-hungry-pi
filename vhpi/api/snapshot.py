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

import os
from glob import glob
import subprocess as sub
import time
import re
from itertools import chain
from typing import Union, List, NamedTuple
from vhpi.api.logging import ts_msg
import vhpi.api.logging as log
from vhpi.utils import clean_path, load_yaml, save_yaml
from vhpi.api.types import BackupRoot, BackupLatest, SnapDir, SnapDirTmp, \
    Interval, KeepAmount, Job
import vhpi.constants as const


class Snap(NamedTuple):
    backup_root: BackupRoot
    src: BackupLatest
    dst_base: str
    dst: SnapDir
    dst_tmp: SnapDirTmp
    interval: Interval
    keep_amount: KeepAmount


def _create_hardlinks(snap: Snap) -> None:
    """
    Create hard-links with unix cp tool.
    """
    if os.path.exists(snap.dst_tmp):
        raise FileExistsError(f'Hardlink destination already exists.')

    log.debug(ts_msg(4, f'Create hardlinks: {snap.src.split("/")[-1]} '
                        f'-> {snap.dst_tmp.split("/")[-1]}'))

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


def _shift(snap: Snap) -> None:
    """
    Increase the num in the dir by one for selected snapshot interval type.
    """
    log.debug(
        ts_msg(4, f'Shift snapshot "{snap.interval}" in {snap.backup_root}'))

    len_base = len(snap.dst_base)

    for path in glob(snap.dst_base + '[0-9]_[0-9]*'):
        num = re.match('[0-9]+', path[len_base:]).group()
        num = int(num)

        pattern = f'{snap.dst_base}{num}'
        replacement = f'{snap.dst_base}{num+1}'

        new_path = re.sub(pattern, replacement, path)

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
    keep_range: list = range(0, snap.keep_amount)

    snaps_to_keep: Union[List[SnapDir], list] = [
        glob(f'{snap.dst_base}{str(num)}_[0-9]*')
        for num
        in keep_range
    ]

    snaps_to_keep = list(chain.from_iterable(snaps_to_keep))

    deprecated: Union[List[SnapDir], list] = [
        _dir
        for _dir
        in glob(snap.dst_base + '*')
        if _dir not in snaps_to_keep
    ]

    return deprecated


def _rm_snap(dir_: Union[SnapDir, SnapDirTmp]) -> None:
    """
    Remove Snapshot directory.
    Uses unix rm instead of shutil.rmtree for better performance.
    """
    log.debug(
        ts_msg(
            ind=4,
            msg=f'Remove deprecated snapshot: {os.path.basename(dir_)}'
        )
    )

    sub.check_call(['rm', '-rf', dir_])


def _rm_deprecated_snaps(snap: Snap):
    """
    Delete deprecated snapshot directories.
    """
    deprecated = _get_deprecated_snaps(snap)

    for snap_dir in deprecated:
        log.debug(ts_msg(4, f'Deleting deprecated snapshot: {snap_dir}'))

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
    log.debug(ts_msg(4, f'Update timestamp for "{snap.interval}".'))

    timestamp_file = clean_path(
        f'{snap.backup_root}/{const.TIMESTAMP_FILE_NAME}'
    )
    timestamps = load_yaml(timestamp_file, True) or {}

    timestamps[snap.interval] = time.strftime(const.TIMESTAMP_FORMAT)

    save_yaml(timestamps, timestamp_file)


def _init_snapshot(
    interval: Interval,
    job: Job,
) -> Snap:
    """"""
    dst_base = clean_path(f'{job.backup_root}/{interval}_')
    dst = f'{dst_base}0'
    dst_tmp = f'{dst}_tmp'

    snap = Snap(
        backup_root=job.backup_root,
        src=job.backup_latest,
        dst_base=dst_base,
        dst=dst,
        dst_tmp=dst_tmp,
        interval=interval,
        keep_amount=job.snapshots.get(interval),
    )
    return snap


def make(
    interval: Interval,
    job: Job,
) -> None:
    """
    Create a new snapshot from 'backup.latest'.
    """

    log.debug('')
    log.debug(
        ts_msg(4, f'Start snapshot sequence: "{interval}" for: '
                  f'{job.backup_src}')
    )

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
        dst=f'{snap.dst}_{time.strftime("%Y-%m-%d")}_'
            f'{time.strftime("%H:%M:%S")}'
    )

    _rm_deprecated_snaps(snap)

    _update_timestamp(snap)


def routine(job: Job):
    for interval in job.due_snapshots:
        make(
            interval=interval,
            job=job,
        )
