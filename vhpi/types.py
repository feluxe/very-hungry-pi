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
from dataclasses import dataclass
from typing import Any

# The source path that is backup-ed.
BackupSrc = str

# The dir that contains 'backup.latest' and all snapshot dirs for backup source.
BackupRoot = str

# The backup.latest dir, which is the destination for rsync.
# It's located in BackupRoot.
BackupLatest = str

# A snapshot dir, e.g hourly.0, daily.2, etc.
# Each SnapDir is located in BackupRoot.
SnapshotDir = str

# The dir that contains the unfinished snapshot that is currently, created.
# For the time it exists it's located in BackupRoot.
SnapshotDirTmp = str

# The name of the interval, e.g 'hourly', 'daily', 'weekly', etc.
SnapshotName = str

# The duration of an interval, e.g. hourly: 3600.
SnapshotInterval = int
SnapshotIntervals = dict[SnapshotName, SnapshotInterval]

# The amount of snapshots that should be kept for an Interval.
SnapshotKeepAmount = int
SnapshotKeepAmounts = dict[SnapshotName, SnapshotKeepAmount]

# The interval timestamp e.g. "2020-01-02 00:00:00"
SnapshotTimestamp = str
SnapshotTimestamps = dict[SnapshotName, SnapshotTimestamp]


@dataclass
class App:
    version: str
    home_dir: str
    root_dir: str
    cfg_dir: str
    cfg_file: str
    log_dir: str
    timestamp_file_name: str
    timestamp_format: str


@dataclass
class Job:
    name: str
    login_token: bytes
    source_ip: str
    backup_src: BackupSrc
    backup_root: BackupRoot
    backup_latest: BackupLatest
    rsync_options: str
    exclude_lib: dict[str, list[str]]
    exclude_lists: list[str]
    excludes: list[str]
    init_time: float
    snapshot_timestamps: SnapshotTimestamps
    snapshot_intervals: SnapshotIntervals
    jobs_raw: dict[str, Any]


@dataclass
class Snapshot:
    dst_tmp: SnapshotDirTmp
    base_pattern: str
    name: SnapshotName
    keep_amount: SnapshotKeepAmount
    last_completion_at: SnapshotTimestamp
    is_due: bool
