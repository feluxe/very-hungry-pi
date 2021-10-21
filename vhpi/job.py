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
import time
from typing import Any

from . import lib, rsync, snapshot
from .logging import log
from .types import App, BackupRoot, Job, Snapshot, SnapshotIntervals, SnapshotTimestamps


def _validate_src_and_dst(backup_src, backup_root) -> bool:

    if not isinstance(backup_src, str):
        log.lvl0_cfg_type_error("rsync_src", "string")
        return False

    if not isinstance(backup_root, str):
        log.lvl0_cfg_type_error("rsync_dst", "string")
        return False

    if backup_src == "":
        log.lvl0_cfg_empty_item("rsync_src")
        return False

    if backup_root == "":
        log.lvl0_cfg_empty_item("rsync_dst")
        return False

    if backup_src.split(":")[-1][0] != "/":
        log.lvl0_cfg_no_absolute_path_error("rsync_src")
        return False

    if ":" in backup_root:
        log.lvl0_cfg_backup_dst_must_be_local()
        return False

    if backup_root[0] != "/":
        log.lvl0_cfg_no_absolute_path_error("rsync_dst")
        return False

    if not os.path.isdir(backup_root):
        log.lvl0_cfg_dst_not_exists_error(backup_root)
        return False

    return True


def _load_snapshot_timestamps(
    app: App,
    snapshot_intervals: SnapshotIntervals,
    backup_root: BackupRoot,
) -> SnapshotTimestamps:

    timestamp_file = lib.clean_path(f"{backup_root}/{app.timestamp_file_name}")

    # Create empty timestamps file if necessary.
    if not os.path.isfile(timestamp_file):
        open(timestamp_file, "a").close()

    timestamps: SnapshotTimestamps = lib.load_yaml(timestamp_file) or {}

    for interval in snapshot_intervals:
        if not timestamps.get(interval):
            timestamps.update({interval: "1970-01-02 00:00:00"})

    return timestamps


def get_job(app: App, job_raw: dict[str, Any], user_cfg_raw: dict[str, Any]) -> Job:

    user_app_cfg = user_cfg_raw.get("app_cfg", {})

    snapshot_intervals: SnapshotIntervals = user_app_cfg.get("intervals", {})

    backup_src = job_raw.get("rsync_src", "no-src-given")
    backup_root = job_raw.get("rsync_dst", "no-dst-given")
    snapshot_timestamps = _load_snapshot_timestamps(
        app, snapshot_intervals, backup_root
    )

    return Job(
        name=job_raw.get("name", "job-with-no-name"),
        login_token=job_raw["login_token"],
        source_ip=job_raw.get("source_ip", "no-ip-given"),
        backup_src=backup_src,
        backup_root=backup_root,
        backup_latest=f"{backup_root}/backup.latest",
        rsync_options=job_raw.get("rsync_options", ""),
        exclude_lib=user_app_cfg.get("exclude_lib", {}),
        exclude_lists=job_raw.get("exclude_lists", []),
        excludes=job_raw.get("excludes", []),
        init_time=time.time(),
        snapshot_timestamps=snapshot_timestamps,
        snapshot_intervals=snapshot_intervals,
        jobs_raw=user_cfg_raw.get("jobs", []),
    )


def _duty_check_routine(job: Job, due_snapshots: list[Snapshot]) -> bool:

    if not due_snapshots:
        log.lvl0_skip_info(
            online=True,
            due_jobs=due_snapshots,
            ip=job.source_ip,
            path=job.backup_src,
        )
        return False

    if not lib.is_machine_online(source_ip=job.source_ip):
        log.lvl0_skip_info(
            online=False,
            due_jobs=due_snapshots,
            ip=job.source_ip,
            path=job.backup_src,
        )
        return False

    return True


def run(app: App, job_raw: dict[str, Any], user_cfg_raw: dict[str, Any]) -> None:

    if not _validate_src_and_dst(job_raw["rsync_src"], job_raw["rsync_dst"]):
        return

    job = get_job(app, job_raw, user_cfg_raw)

    snapshots = [
        snapshot.get_snapshot(
            app,
            job,
            name,
            keep_amount,
            job.snapshot_timestamps[name],
        )
        for name, keep_amount in job_raw["snapshots"].items()
    ]

    due_snapshots = [snapshot for snapshot in snapshots if snapshot.is_due]

    if not _duty_check_routine(job, due_snapshots):
        return

    log.lvl0_job_start_info(job, due_snapshots)

    if not rsync.run(app, job):
        return

    for s in due_snapshots:
        snapshot.run(app, job, s)

    log.lvl0_job_out_info(
        completed=True,
        init_time=job.init_time,
    )
