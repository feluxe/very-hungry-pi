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
import time
from math import ceil
import logging
import logging.config
from logging.handlers import RotatingFileHandler
import vhpi.constants as const
from typing import List
from vhpi.api.types import Interval


############
# Messages #
############

def _job_start_info(
    ip: str,
    src: str,
    due_snapshots: List[Interval],
) -> str:
    """
    Log message for starting a new backup job
    """
    msg: str = time.strftime(const.TIMESTAMP_FORMAT)
    msg += ' [Executing] ' + ip + '\t' + src + '\n'
    msg += '\n    Due: ' + ', '.join(due_snapshots)

    return info(msg)


def _job_out_info(
    init_time: float,
    message: str = '',
    completed: bool = False,
    skipped: bool = False,
    failed: bool = False,
    unknown: bool = False,
) -> str:
    """
    This message is used to log execution results of a job.
    """
    seconds: float = time.time() - init_time
    duration: int = time.strftime('%H:%M:%S', time.gmtime(seconds))
    new_msg = ''

    if completed:
        new_msg += f'[Completed] after: {duration} (h:m:s) {message}'

    elif skipped:
        new_msg += f'[Skipped] {message}'

    elif failed:
        new_msg += f'[Failed] after: {duration} (h:m:s) {message}'

    elif unknown:
        new_msg += f'[Job Result Unknown] after: {duration} (h:m:s) {message}'

    info(f'\n{time.strftime(const.TIMESTAMP_FORMAT)} {new_msg}')


def _fix_len(
    string: str,
    limit: int,
    filler: str = '.',
    rpl: str = '[...]'
) -> str:
    """
    Force a string to be of certain length. E.g.:
    'Hello, I am [...] see you all!'  (Input str was longer than 30)
    'Ciao!.........................'  (Input str was shorter than 30)
    @filler: The type of char that is used to fill gaps.
    @rpl: A string that is  replacing the part of the input string which was cut
    out.
    """
    output = ''
    str_len: int = len(string)

    if str_len == limit:
        output: str = string

    elif str_len > limit:
        cut_len: int = str_len + len(rpl) - limit
        slice_start: int = ceil((str_len - cut_len) / 2)
        slice_end: int = slice_start + cut_len

        if cut_len <= str_len:
            output: str = string.replace(string[slice_start:slice_end], rpl)

        else:
            output: str = rpl

        if len(output) > limit:
            output: str = output[:limit - len(output)]

    elif str_len < limit:
        output: str = string + (filler * (limit - str_len))

    return output


def _skip_info(
    online: bool,
    due_jobs: list,
    ip: str,
    path: str
) -> str:
    """
    This message is used to log a single line, that says a job is fine, but
    not due or the source is offline.
    """
    state: str = 'online' if online else 'offline'
    due_jobs: list = due_jobs or []
    ip_str: str = _fix_len(ip, 15, " ")
    path_str: str = _fix_len(path, 50, "·")
    state_str: str = _fix_len(state, 7, " ")
    due_jobs_str: str = ', '.join(sorted(due_jobs))
    due_str: str = f'Due: {due_jobs_str}' if due_jobs else 'No due jobs'

    msg = f'[Skipped] [{ip_str}] [{path_str}] [Source {state_str}] [{due_str}]'

    info(f'{time.strftime(const.TIMESTAMP_FORMAT)} {msg}')


def _cfg_type_error(
    item: str,
    type_: str,
) -> None:
    error(
        f'[Error] Invalid config. "{item}" must be of type {type_}.'
    )


def _cfg_no_absolute_path_error(item: str) -> None:
    error(
        f'[Error] Invalid config. Please provide an absolute path for "{item}".'
    )


def _cfg_dst_not_exists_error(item: str) -> None:
    error(
        f'[Error] Backup destination does not exist: "{item}".'
    )


def _ts_msg_lvl0(
    msg: str = ''
) -> str:
    """
    Create a message preceding a timestamp.
    """
    ts: str = time.strftime(const.TIMESTAMP_FORMAT)

    return f'{ts} {msg}'


class lvl0:
    job_start_info = _job_start_info
    job_out_info = _job_out_info
    skip_info = _skip_info
    cfg_type_error = _cfg_type_error
    cfg_no_absolute_path_error = _cfg_no_absolute_path_error
    cfg_dst_not_exists_error = _cfg_dst_not_exists_error
    ts_msg = _ts_msg_lvl0


def _backup_src_not_exist_error(backup_src: str) -> None:
    error(
        f'    Error: Backup source does not exist.": {backup_src}'
    )


def _backup_dst_invalid_error(backup_dst: str) -> None:
    error(
        f'    Error: Invalid Destination: {backup_dst}'
    )


def _ts_msg_lvl1(
    msg: str = ''
) -> str:
    """
    Create a message preceding a timestamp.
    """
    ts: str = time.strftime(const.TIMESTAMP_FORMAT)

    return f'    {ts} {msg}'


class lvl1():
    backup_src_not_exist_error = _backup_src_not_exist_error
    backup_dst_invalid_error = _backup_dst_invalid_error
    ts_msg = _ts_msg_lvl1


##########
# logger #
##########

def init(log_output_dir: str) -> None:
    global logger, info, debug, warning, error, critical

    if logger:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    logfile_debug_handler = RotatingFileHandler(
        filename=f'{log_output_dir}/debug.log',
        maxBytes=1073741824,
        backupCount=1,
    )

    logfile_info_handler = logging.FileHandler(
        filename=f'{log_output_dir}/info.log',
    )

    console_debug_handler = logging.StreamHandler(
        stream=sys.stdout
    )

    logfile_debug_handler.setLevel(logging.DEBUG)
    logfile_info_handler.setLevel(logging.INFO)
    console_debug_handler.setLevel(logging.DEBUG)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    logger.addHandler(logfile_debug_handler)
    logger.addHandler(logfile_info_handler)
    logger.addHandler(console_debug_handler)

    info = logger.info
    debug = logger.debug
    warning = logger.warning
    error = logger.error
    critical = logger.critical


logger = logging.getLogger()
info = logger.info
debug = logger.debug
warning = logger.warning
error = logger.error
critical = logger.critical
