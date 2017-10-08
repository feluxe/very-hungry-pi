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


def job_start_msg(
    ip: str,
    src: str,
    due_snapshots: list,
) -> str:
    """
    Log message for starting a new backup job
    """
    msg: str = time.strftime(const.TIMESTAMP_FORMAT)
    msg += ' [Executing] ' + ip + '\t' + src + '\n'
    msg += '\n    Due: ' + ', '.join(due_snapshots)

    return msg


def job_out_msg(
    code: int,
    timestamp: int,
    message: str = ''
) -> str:
    """
    Log message used when a job ends.
    """
    seconds = time.time() - timestamp
    duration = time.strftime('%H:%M:%S', time.gmtime(seconds))
    new_msg = ''

    if code == 0:
        new_msg += f'[Completed] after: {duration} (h:m:s) {message}'

    elif code == 1:
        new_msg += f'[Skipped] {message}'

    elif code == 2:
        new_msg += f'[Failed] after: {duration} (h:m:s) {message}'

    else:
        new_msg += f'[Job Result Unknown] after: {duration} (h:m:s) {message}'

    return f'\n{time.strftime(const.TIMESTAMP_FORMAT)} {new_msg}'


def skip_msg(
    online: bool,
    due_jobs: list,
    ip: str,
    path: str
) -> str:
    """
    Log message for Skipping a backup.
    """
    state: str = 'online' if online else 'offline'
    due_jobs: list = due_jobs or []
    ip_str: str = fix_len(ip, 15, " ")
    path_str: str = fix_len(path, 50, "·")
    state_str: str = fix_len(state, 7, " ")
    due_jobs_str: str = ', '.join(sorted(due_jobs))
    due_str: str = f'Due: {due_jobs_str}' if due_jobs else 'No due jobs'

    msg = f'[Skipped] [{ip_str}] [{path_str}] [Source {state_str}] [{due_str}]'

    return time.strftime(const.TIMESTAMP_FORMAT) + ' ' + msg


def ts_msg(
    ind: int = 4,
    msg: str = ''
) -> str:
    """
    Create a message preceding a timestamp.
    """
    ind = ''.join([' ' for i in range(0, ind)])
    ts = time.strftime(const.TIMESTAMP_FORMAT)

    return f'{ind}{ts} {msg}'


def fix_len(
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
    str_len = len(string)

    if str_len == limit:
        output = string

    elif str_len > limit:
        cut_len = str_len + len(rpl) - limit
        slice_start = ceil((str_len - cut_len) / 2)
        slice_end = slice_start + cut_len

        if cut_len <= str_len:
            output = string.replace(string[slice_start:slice_end], rpl)

        else:
            output = rpl

        if len(output) > limit:
            output = output[:limit - len(output)]

    elif str_len < limit:
        output = string + (filler * (limit - str_len))

    return output


def init(log_output_dir):
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
