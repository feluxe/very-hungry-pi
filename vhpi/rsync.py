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
import subprocess as sp
import time
from subprocess import Popen
from typing import Optional, Union

from . import lib
from .logging import log
from .types import App, BackupLatest, Job


def _get_excludes(
    excludes: list,
    excl_lists: list,
    excl_lib: dict,
) -> list[str]:
    for _list in excl_lists:
        for item in excl_lib[_list]:
            excludes.append(item)

    return ['--exclude="' + item + '"' for item in excludes]


def _get_rsync_command(
    rsync_options: str,
    backup_src: str,
    backup_latest: BackupLatest,
    excludes: list,
    excl_lists: list,
    excl_lib: dict,
) -> str:
    """
    Build rsync command from config data.
    @rsync_options: from cfg, e.g.: "-aAHSvX --delete"
    @excludes: from cfg, e.g.: ['downloads', 'tmp']
    @excl_lists: from cfg, e.g.: ['standard_list']
    @excl_lib: from cfg, e.g.: {'standard_list': ['downloads', 'tmp']}
    """
    exclude_flags = _get_excludes(excludes, excl_lists, excl_lib)
    src = lib.clean_path(backup_src)
    dst = lib.clean_path(backup_latest)

    return f"rsync {rsync_options} {''.join(exclude_flags)} {src} {dst}"


def _terminate_sub_process(p: Popen) -> None:
    if p.poll() is None:
        p.terminate()
        if p.poll() is None:
            p.kill()


def _log_line(line: str) -> None:
    line = line.replace("\n", "")

    if "error:" in line:
        log.error(f"    {line}")
    elif "IO error" in line:
        log.error(f"    {line}")
    elif "rsync:" in line:
        log.warning(f"    {line}")
    elif "warning:" in line:
        log.warning(f"    {line}")
    elif "bytes/sec" in line:
        log.info(f"    {line}")
    elif "total size is " in line:
        log.info(f"    {line}")
    elif line.strip():
        log.debug(f"    {line}")


def _log_job_out_rsync_failed(init_time: float) -> None:
    log.lvl0_job_out_info(
        message="Rsync Execution Failed.",
        skipped=True,
        init_time=init_time,
    )


def _handle_rsync_result(result: Union[str, int], init_time: float) -> bool:

    if result == "source_offline":
        log.error(log.lvl1_ts_msg("Error: Source machine went offline"))
        _log_job_out_rsync_failed(init_time)
        return False

    elif result == "permission_denied":
        log.error(log.lvl1_ts_msg("Error: SSH Login failed."))
        _log_job_out_rsync_failed(init_time)
        return False

    elif result == "no_dst":
        log.error(log.lvl1_ts_msg("Error: Backup Destination not available."))
        _log_job_out_rsync_failed(init_time)
        return False

    elif result == 20:
        log.error(log.lvl1_ts_msg("Error Code 20: Source machine went offline"))
        _log_job_out_rsync_failed(init_time)
        return False

    return True


# def _rsync_output(p: Popen) -> None:
#     for line in p.stdout:
#         _log_line(line)


# def _async_log_subprocess_output(p: Popen) -> None:
#     output_stream = threading.Thread(target=_rsync_output, args=(p,))
#     output_stream.setDaemon(True)
#     output_stream.start()


def _run_rsync_process(job: Job) -> Union[str, int]:

    rsync_command: str = _get_rsync_command(
        rsync_options=job.rsync_options,
        backup_src=job.backup_src,
        backup_latest=job.backup_latest,
        excludes=job.excludes,
        excl_lists=job.exclude_lists,
        excl_lib=job.exclude_lib,
    )

    log.debug("    Executing: " + rsync_command)
    log.debug("")

    if job.login_token:
        rsync_command = (
            'sshpass -p "' + lib.read_login(job.login_token) + '" ' + rsync_command
        )

    p = Popen(
        rsync_command,
        shell=True,
        stdin=sp.PIPE,
        stdout=sp.PIPE,
        stderr=sp.STDOUT,
        close_fds=True,
        universal_newlines=True,
    )

    duration_seconds = 1

    while True:

        return_code: Optional[int] = p.poll()

        # break if subprocess finished naturally.
        if return_code is not None:

            # Log what is left in buffer.
            if p.stdout:
                _log_line(p.stdout.read())

            return return_code

        if p.stdout:
            for line in p.stdout.readlines():
                _log_line(line)

                if "Permission denied, please try again" in line:
                    _terminate_sub_process(p)
                    return "permission_denied"

        if not lib.is_machine_online(job.source_ip):
            _terminate_sub_process(p)
            return "source_offline"

        if not os.path.isdir(job.backup_root):
            _terminate_sub_process(p)
            return "no_dst"

        time.sleep(duration_seconds)


def run(app: App, job: Job) -> bool:

    log.info("\n    [Rsync Log]")
    log.debug("")
    log.debug(log.lvl1_ts_msg("Start: rsync execution."))

    try:
        result: Union[str, int] = _run_rsync_process(job)

        if not _handle_rsync_result(result=result, init_time=job.init_time):
            return False

    except sp.SubprocessError as e:
        log.error(log.lvl1_ts_msg("Error: An error occurred in the rsync subprocess."))

        log.debug(e)

        _log_job_out_rsync_failed(job.init_time)

        return False

    log.debug("")
    log.debug(log.lvl1_ts_msg("End: rsync execution."))

    return True
