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

import time
import threading
import subprocess as sp
from subprocess import Popen
from typing import List, Optional, Union
from vhpi.utils import clean_path
from vhpi.api.types import BackupLatest, Job, Settings
from vhpi.api import validate
import vhpi.api.logging as log


def _build_excludes(
    excludes: list,
    excl_lists: list,
    excl_lib: dict,
) -> List[str]:
    """
    """
    for _list in excl_lists:
        for item in excl_lib[_list]:
            excludes.append(item)

    return ['--exclude=' + item for item in excludes]


def _build_rsync_command(
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
    options: List[str] = rsync_options.split()
    excludes: List[str] = _build_excludes(excludes, excl_lists, excl_lib)
    src: str = clean_path(backup_src)
    dst: str = clean_path(backup_latest)

    return ['rsync'] + options + excludes + [src, dst]


def _terminate_sub_process(p: Popen) -> None:
    if p.poll() is None:
        p.terminate()
        if p.poll() is None:
            p.kill()


def _run_rsync_monitor(
    job: Job,
    sub_process: Popen
) -> Union[str, int]:
    """"""
    duration: int = 1

    while True:
        return_code: Optional[int] = sub_process.poll()

        # break if subprocess finished naturally.
        if return_code is not None:
            return return_code

        if not validate.is_machine_online(job.source_ip):
            _terminate_sub_process(sub_process)
            return 'source_offline'

        if not validate.backup_src_exists(job.backup_src):
            _terminate_sub_process(sub_process)
            return 'no_src'

        if not validate.backup_dst_is_dir(job.backup_root):
            _terminate_sub_process(sub_process)
            return 'no_dst'

        duration: int = 60 if duration > 60 else duration * 2

        time.sleep(duration)


def _log_line(line: str) -> None:
    line = line.replace('\n', '')

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
    elif line.strip():
        log.debug(f'    {line}')


def _log_job_out_rsync_failed(init_time: float) -> None:
    log.lvl0.job_out_info(
        message='Rsync Execution Failed.',
        skipped=True,
        init_time=init_time,
    )


def handle_monitor_result(
    result: Union[str, int],
    init_time: float
) -> bool:
    if result == 'source_offline':
        log.error(log.lvl1.ts_msg('Error: Source machine went offline'))
        _log_job_out_rsync_failed(init_time)
        return False

    if result == 'no_src':
        log.error(log.lvl1.ts_msg('Error: Backup Source not available.'))
        _log_job_out_rsync_failed(init_time)
        return False

    if result == 'no_dst':
        log.error(log.lvl1.ts_msg('Error: Backup Destination not available.'))
        _log_job_out_rsync_failed(init_time)
        return False

    return True


def _handle_rsync_return_codes(
    return_code: Union[str, int],
    init_time: float
) -> bool:
    """"""
    if return_code == 20:
        log.error(log.lvl1.ts_msg('Error Code 20: Source machine went offline'))
        _log_job_out_rsync_failed(init_time)
        return False

    return True


def _rsync_output(p: Popen) -> None:
    for line in p.stdout:
        _log_line(line)


def _async_log_subprocess_output(p: Popen) -> None:
    output_stream = threading.Thread(
        target=_rsync_output,
        args=(p,)
    )
    output_stream.setDaemon(True)
    output_stream.start()


def exec_rsync(
    job: Job,
    settings: Settings
) -> bool:
    """"""
    rsync_command: List[str] = _build_rsync_command(
        rsync_options=job.rsync_options,
        backup_src=job.backup_src,
        backup_latest=job.backup_latest,
        excludes=job.excludes,
        excl_lists=job.exclude_lists,
        excl_lib=settings.exclude_lib,
    )

    log.info('\n    [Rsync Log]')
    log.debug('')
    log.debug(log.lvl1.ts_msg('Start: rsync execution.'))

    try:
        log.debug('    Executing: ' + ' '.join(rsync_command))
        log.debug('')

        p = Popen(
            rsync_command,
            shell=False,
            stdin=sp.PIPE,
            stdout=sp.PIPE,
            stderr=sp.STDOUT,
            close_fds=True,
            universal_newlines=True
        )

        _async_log_subprocess_output(p)

        monitor_result: Union[str, int] = _run_rsync_monitor(job, p)

        if not handle_monitor_result(
            result=monitor_result,
            init_time=job.init_time,
        ):
            return False

        if not _handle_rsync_return_codes(
            return_code=monitor_result,
            init_time=job.init_time
        ):
            return False

    except sp.SubprocessError as e:
        log.error(log.lvl1.ts_msg(
            'Error: An error occurred in the rsync subprocess.'
        ))

        log.debug(e)

        _log_job_out_rsync_failed(job.init_time)

        return False

    log.debug('')
    log.debug(log.lvl1.ts_msg('End: rsync execution.'))

    return True
