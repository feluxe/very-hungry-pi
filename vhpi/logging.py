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

import logging
import logging.config
import sys
import time
from logging.handlers import RotatingFileHandler
from math import ceil

from .types import App, Job, Snapshot


def _fix_len(string: str, limit: int, filler: str = ".", rpl: str = "[...]") -> str:
    """
    Force a string to be of certain length. E.g.:
    'Hello, I am [...] see you all!'  (Input str was longer than 30)
    'Ciao!.........................'  (Input str was shorter than 30)
    @filler: The type of char that is used to fill gaps.
    @rpl: A string that is  replacing the part of the input string which was cut
    out.
    """
    output = ""
    str_len: int = len(string)

    if str_len == limit:
        output = string

    elif str_len > limit:
        cut_len: int = str_len + len(rpl) - limit
        slice_start: int = ceil((str_len - cut_len) / 2)
        slice_end: int = slice_start + cut_len

        if cut_len <= str_len:
            output = string.replace(string[slice_start:slice_end], rpl)

        else:
            output = rpl

        if len(output) > limit:
            output = output[: limit - len(output)]

    elif str_len < limit:
        output = string + (filler * (limit - str_len))

    return output


def get_info_handler(app: App):
    handler = RotatingFileHandler(
        filename=f"{app.log_dir}/info.log",
        maxBytes=1073741824,
        backupCount=1,
    )
    handler.setLevel(logging.INFO)
    return handler


def get_debug_handler(app: App):
    handler = RotatingFileHandler(
        filename=f"{app.log_dir}/debug.log",
        maxBytes=1073741824,
        backupCount=1,
    )
    handler.setLevel(logging.DEBUG)

    return handler


def get_console_debug_handler():
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.DEBUG)
    return handler


class Log:
    def __init__(self):

        self.timestamp_format = ""

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        self.debug = self.logger.debug
        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.critical = self.logger.critical

    def update(self, app: App):

        self.timestamp_format = app.timestamp_format

        self.logger.addHandler(get_info_handler(app))
        self.logger.addHandler(get_debug_handler(app))
        self.logger.addHandler(get_console_debug_handler())

    # LOG LEVEL 0
    # ===========

    def lvl0_job_start_info(
        self,
        job: Job,
        due_snapshots: list[Snapshot],
    ):
        """
        Log message for starting a new backup job
        """
        msg = time.strftime(self.timestamp_format)
        msg += " [Executing] " + job.source_ip + "\t" + job.backup_src + "\n"
        msg += "\n    Due: " + ", ".join([s.name for s in due_snapshots])

        self.logger.info(msg)

    def lvl0_job_out_info(
        self,
        init_time: float,
        message: str = "",
        completed: bool = False,
        skipped: bool = False,
        failed: bool = False,
        unknown: bool = False,
    ):
        """
        This message is used to log execution results of a job.
        """
        seconds: float = time.time() - init_time
        duration: str = time.strftime("%H:%M:%S", time.gmtime(seconds))
        new_msg = ""

        if completed:
            new_msg += f"[Completed] after: {duration} (h:m:s) {message}"

        elif skipped:
            new_msg += f"[Skipped] {message}"

        elif failed:
            new_msg += f"[Failed] after: {duration} (h:m:s) {message}"

        elif unknown:
            new_msg += f"[Job Result Unknown] after: {duration} (h:m:s) {message}"

        return self.logger.info(f"\n{time.strftime(self.timestamp_format)} {new_msg}")

    def lvl0_skip_info(
        self,
        online: bool,
        due_jobs: list,
        ip: str,
        path: str,
    ) -> str:
        """
        This message is used to log a single line, that says a job is fine, but
        not due or the source is offline.
        """
        state = "online" if online else "offline"
        due_jobs = due_jobs or []
        ip_str = _fix_len(ip, 15, " ")
        path_str = _fix_len(path, 50, "·")
        state_str = _fix_len(state, 7, " ")
        due_jobs_str = ", ".join(sorted(due_jobs))
        due_str = f"Due: {due_jobs_str}" if due_jobs else "No due jobs"

        msg = f"[Skipped] [{ip_str}] [{path_str}] [Source {state_str}] [{due_str}]"

        return self.logger.info(f"{time.strftime(self.timestamp_format)} {msg}") or ""

    def lvl0_cfg_type_error(
        self,
        item: str,
        type_: str,
    ):
        self.logger.error(f'[Error] Invalid config. "{item}" must be of type {type_}.')

    def lvl0_cfg_empty_item(self, item: str):
        self.logger.error(
            f'[Error] Invalid config. Please provide a value for "{item}".'
        )

    def lvl0_cfg_backup_dst_must_be_local(self):
        self.logger.error(
            f"[Error] Invalid config. The backup destination must be a local directory."
        )

    def lvl0_cfg_no_absolute_path_error(self, item: str):
        self.logger.error(
            f'[Error] Invalid config. Please provide an absolute path for "{item}".'
        )

    def lvl0_cfg_dst_not_exists_error(self, item: str):
        self.logger.error(f'[Error] Backup destination does not exist: "{item}".')

    def lvl0_ts_msg(self, msg: str = "") -> str:
        """
        Create a message preceding a timestamp.
        """
        ts = time.strftime(self.timestamp_format)

        return f"{ts} {msg}"

    # LOG LEVEL 1
    # ===========

    def lvl1_backup_src_not_exist_error(self, backup_src: str):
        self.logger.error(f'    Error: Backup source does not exist.": {backup_src}')

    def lvl1_backup_dst_invalid_error(self, backup_dst: str):
        self.logger.error(f"    Error: Invalid Destination: {backup_dst}")

    def lvl1_ts_msg(self, msg: str = "") -> str:
        """
        Create a message preceding a timestamp.
        """
        ts = time.strftime(self.timestamp_format)

        return f"    {ts} {msg}"


log = Log()
