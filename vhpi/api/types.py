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

from typing import NamedTuple, Dict, List

# The source path that is backup-ed.
BackupSrc = str

# The dir that contains 'backup.latest' and all snapshot dirs for backup source.
BackupRoot = str

# The backup.latest dir, which is the destination for rsync.
# It's located in BackupRoot.
BackupLatest = str

# A snapshot dir, e.g hourly.0, daily.2, etc.
# Each SnapDir is located in BackupRoot.
SnapDir = str

# The dir that contains the unfinished snapshot that is currently, created.
# For the time it exists it's located in BackupRoot.
SnapDirTmp = str

# The name of the interval, e.g 'hourly', 'daily', 'weekly', etc.
Interval = str

# The amount of snapshots that should be kept for an Interval.
KeepAmount = int

# The duration of an interval, e.g. hourly: 3600.
IntervalDuration = int


class Settings(NamedTuple):
    exclude_lib: dict
    intervals: Dict[Interval, IntervalDuration]


class Job(NamedTuple):
    init_time: int
    name: str
    source_ip: str
    backup_src: BackupSrc
    backup_root: BackupRoot
    backup_latest: BackupLatest
    rsync_options: str
    exclude_lists: list
    excludes: list
    snapshots: Dict[Interval, KeepAmount]
    timestamps: Dict[Interval, IntervalDuration]
    due_snapshots: List[Interval]
