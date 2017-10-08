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
import glob
import subprocess as sub
import time
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
    Increase the dir num by one for selected snapshot interval type.
    """
    log.debug(
        ts_msg(4, f'Shift snapshot "{snap.interval}" in {snap.backup_root}'))

    base_name = clean_path(f'{snap.backup_root}/{snap.interval}.')

    for i in reversed(range(0, len(glob.glob(base_name + '*[0-9]')))):
        os.rename(
            src=base_name + str(i),
            dst=base_name + str(i + 1)
        )


def _get_deprecated_snaps(snap: Snap) -> Union[List[SnapDir], list]:
    """
    Get all deprecated snapshot dirs.
    Dirs that contain snapshots that are older than what the user wants to keep.
    The keep range is defined in the config yaml file.
    """
    base_dir: str = clean_path(f'{snap.backup_root}/{snap.interval}.')
    keep_range: list = range(0, snap.keep_amount)

    snaps_to_keep: Union[List[SnapDir], list] = [
        base_dir + str(num)
        for num
        in keep_range
    ]

    deprecated: Union[List[SnapDir], list] = [
        _dir
        for _dir
        in glob.glob(base_dir + '*')
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

    timestamp_file = f'{snap.backup_root}/{const.TIMESTAMP_FILE_NAME}'
    timestamps = load_yaml(timestamp_file, True) or {}

    timestamps[snap.interval] = time.strftime(const.TIMESTAMP_FORMAT)

    save_yaml(timestamps, timestamp_file)


def _init_snapshot(
    interval: Interval,
    job: Job,
) -> Snap:
    """"""
    dst_base = clean_path(f'{job.backup_root}/{interval}.')
    dst = f'{dst_base}0'
    dst_tmp = f'{dst}.tmp'

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

    if os.path.exists(snap.dst):
        _shift(snap)

    os.rename(
        src=snap.dst_tmp,
        dst=snap.dst
    )

    _rm_deprecated_snaps(snap)

    _update_timestamp(snap)


def routine(job: Job):
    for interval in job.due_snapshots:
        make(
            interval=interval,
            job=job,
        )
