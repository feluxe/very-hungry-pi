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

import subprocess as sp
from typing import List
from vhpi.utils import clean_path
from vhpi.api.types import BackupLatest, Job
from vhpi.api import health
from vhpi.api.logging import ts_msg
import vhpi.api.logging as log


def build_excludes(
    excludes: list,
    excl_lists: list,
    excl_lib: dict,
):
    """
    """
    for _list in excl_lists:
        for item in excl_lib[_list]:
            excludes.append(item)

    return ['--exclude=' + item for item in excludes]


def build_rsync_command(
    rsync_options: str,
    backup_src: str,
    backup_latest: BackupLatest,
    excludes: list,
    excl_lists: list,
    excl_lib: dict,
) -> List[str]:
    """
    Build rsync command from config data.
    @options: from cfg, e.g.: "-aAHSvX --delete"
    @excludes: from cfg, e.g.: ['downloads', 'tmp']
    @excl_lists: from cfg, e.g.: ['standard_list']
    @excl_lib: from cfg, e.g.: {'standard_list': ['downloads', 'tmp']}
    """
    options = rsync_options.split()
    excludes = build_excludes(excludes, excl_lists, excl_lib)
    src = clean_path(backup_src)
    dst = clean_path(backup_latest)

    return ['rsync'] + options + excludes + [src, dst]


def matching_lines(self, level, needle, lines):
    """Filter a multi-line string for words.
    Each line that contains a certain word will be logged.
    Can be used on the output of rsync to log each line with an 'error' or
    'warning'.
    """
    lines = lines.splitlines()
    matches = ['    ' + level.title() + ': ' + s
               for s in lines if needle in s]
    matches_str = '\n'.join(matches)
    dynamic_func = getattr(self.logger, level)
    dynamic_func(matches_str) if len(matches) > 0 else None


def log_output(output):
    log.debug('\n    [Rsync Log]:')
    log.debug('    ' + output.replace('\n', '\n    '))

    log.info('\n    [Rsync Log Summary]:')

    for line in output.splitlines():
        if 'error:' in line:
            log.error(f'    {line}')
        elif 'IO error' in line:
            log.error(f'    {line}')
        elif 'rsync:' in line:
            log.warning(f'    {line}')
        elif 'warning:' in line:
            log.warning(f'    {line}')
        elif 'bytes/sec' in line:
            log.info(f'    {line}')
        elif 'total size is ' in line:
            log.info(f'    {line}')
    log.info('')


def exec_rsync(rsync_command: list, job: Job):
    log.debug(ts_msg(4, 'Start: rsync execution.'))

    return_val = True

    try:
        log.debug('    Executing: ' + ' '.join(rsync_command))

        p = sp.Popen(
            rsync_command,
            shell=False,
            stdin=sp.PIPE,
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            close_fds=True,
            universal_newlines=True
        )

        health.run_rsync_monitor(job, p)

        # handle rsync exit codes
        output, err = p.communicate()
        log_output(output)

        return_code = p.wait()

        if return_code == 20:
            log.info(
                f'   Info: Skipp current job due to rsync exit code (20)')

            return_val = False

    except sp.SubprocessError as e:
        log.error('    Error: An error occurred in rsync subprocess.')
        log.debug(e)

        return_val = False

    log.debug(ts_msg(4, 'End: rsync execution.\n'))

    return return_val
