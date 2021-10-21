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
import re
import subprocess as sp
import sys
import time
from datetime import datetime
from glob import glob
from typing import Union

from . import lib
from .logging import log
from .types import (
    App,
    Job,
    Snapshot,
    SnapshotDir,
    SnapshotDirTmp,
    SnapshotKeepAmount,
    SnapshotName,
    SnapshotTimestamp,
)


def _is_due(
    app: App,
    job: Job,
    name: SnapshotName,
    timestamp: SnapshotTimestamp,
) -> bool:

    if not timestamp or not isinstance(timestamp, str):
        timestamp = "1970-01-02 00:00:00"

    interval: int = job.snapshot_intervals[name]
    format_ = app.timestamp_format
    timestamp_str = datetime.strptime(timestamp, format_).timetuple()
    timestamp_int = int(time.mktime(timestamp_str))
    time_now = time.time()

    if time_now - timestamp_int >= interval:
        return True
    else:
        return False


def get_snapshot(
    app: App,
    job: Job,
    name: SnapshotName,
    keep_amount: SnapshotKeepAmount,
    timestamp: SnapshotTimestamp,
):

    if name not in job.snapshot_intervals.keys():
        log.critical(f"    Critical: No time interval set for type: {name}")
        sys.exit(1)

    base_pattern = (
        f"{job.backup_root}/[0-9]{4}-[0-9]{2}-[0-9]{2}"
        f"__[0-9]{2}:[0-9]{2}:[0-9]{2}__{name}."
    )

    return Snapshot(
        dst_tmp=lib.clean_path(f"{job.backup_root}/{name}.tmp"),
        base_pattern=base_pattern,
        name=name,
        keep_amount=keep_amount,
        last_completion_at="",
        is_due=_is_due(app, job, name, timestamp),
    )


def _create_hardlinks(job: Job, snapshot: Snapshot) -> None:
    """
    Create hard-links with unix cp tool.
    This creates hardlinks from 'backup.latest' to the snapshot temp dir.
    """
    log.debug(
        log.lvl1_ts_msg(
            f'Create hardlinks: {job.backup_latest.split("/")[-1]} '
            f'-> {snapshot.dst_tmp.split("/")[-1]}'
        )
    )

    cmd = ["cp", "-al", job.backup_latest, snapshot.dst_tmp]

    p = sp.run(cmd, shell=False, stdout=sp.PIPE, stderr=sp.STDOUT, check=False)

    output = p.stdout.decode().strip()

    if output:
        log.debug("\n    " + output)


def _split_number_from_path(path: str) -> tuple[str, int]:

    path_split = path.split(".")
    number = int(path_split[-1])
    path_without_num = ".".join(path_split[:-1]) + "."

    return path_without_num, number


def _get_snapshot_dirs(backup_root: str, snapshot_name: str) -> list[str]:

    return [
        path
        for path in glob(f"{backup_root}/*")
        if re.search(f"__{snapshot_name}\.[0-9]+", path)
    ]


def _shift(job: Job, snapshot: Snapshot) -> None:
    """
    Increase the num in the dir by one for the given snapshot name.
    """
    log.debug(log.lvl1_ts_msg(f'Shift snapshot "{snapshot.name}" in {job.backup_root}'))

    snapshot_dirs_to_shift = _get_snapshot_dirs(job.backup_root, snapshot.name)

    for path in sorted(snapshot_dirs_to_shift, reverse=True):

        path_wo_number, number = _split_number_from_path(path)

        search = f"{path_wo_number}{number}"
        replacement = f"{path_wo_number}{number+1}"

        new_path: str = re.sub(search, replacement, path)

        os.rename(src=path, dst=new_path)


def _get_deprecated_snaps(job: Job, snapshot: Snapshot) -> list[SnapshotDir]:
    """
    Get all deprecated snapshot dirs.
    Dirs that contain snapshots that are older than what the user wants to keep.
    The keep range is defined in the config yaml file.
    """
    return [
        path
        for path in _get_snapshot_dirs(job.backup_root, snapshot.name)
        if _split_number_from_path(path)[1] not in range(0, snapshot.keep_amount)
    ]


def _rm_snap(dir_: Union[SnapshotDir, SnapshotDirTmp]) -> None:
    """
    Remove Snapshot directory.
    Uses unix rm instead of shutil.rmtree for better performance.
    """
    log.debug(log.lvl1_ts_msg(f"Remove deprecated snapshot: {os.path.basename(dir_)}"))

    sp.check_call(["rm", "-rf", dir_])


def _rm_deprecated_snaps(job: Job, snapshot: Snapshot) -> bool:
    """
    Delete deprecated snapshot directories.
    """
    deprecated: Union[list[SnapshotDir], list] = _get_deprecated_snaps(job, snapshot)

    for snap_dir in deprecated:
        try:
            _rm_snap(str(snap_dir))

        except sp.CalledProcessError as e:
            log.debug(e)
            log.error(f"    Error: Could not delete deprecated snapshot: {snap_dir}")
            return False

    return True


def _update_timestamp(app: App, job: Job, snapshot: Snapshot) -> None:

    log.debug(log.lvl1_ts_msg(f'Update timestamp for "{snapshot.name}".'))

    timestamp_file: str = lib.clean_path(f"{job.backup_root}/{app.timestamp_file_name}")
    timestamps: dict[SnapshotName, str] = lib.load_yaml(timestamp_file) or {}

    timestamps[snapshot.name] = time.strftime(app.timestamp_format)

    lib.save_yaml(timestamps, timestamp_file)


def run(app: App, job: Job, snapshot: Snapshot):
    """
    Create a new snapshot from 'backup.latest'.
    """
    timestamp = datetime.fromtimestamp(time.time())

    log.info(f"\n    [Snapshot Log]")
    log.debug("")

    log.debug(
        log.lvl1_ts_msg(
            f'Start snapshot sequence: "{snapshot.name}" for: {job.backup_src}'
        )
    )

    # Remove leftovers.
    if os.path.exists(snapshot.dst_tmp):
        _rm_snap(snapshot.dst_tmp)

    _create_hardlinks(job, snapshot)

    _shift(job, snapshot)

    os.rename(
        src=snapshot.dst_tmp,
        dst=f'{job.backup_root}/{timestamp.strftime("%Y-%m-%d__%H:%M:%S")}__'
        f"{snapshot.name}.0",
    )

    _update_timestamp(app, job, snapshot)

    _rm_deprecated_snaps(job, snapshot)

    log.info(log.lvl1_ts_msg(f"Completed Snapshot: {snapshot.name}"))
    log.debug("")
