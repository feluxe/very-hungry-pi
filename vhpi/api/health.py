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

import time
import sys
import os
import subprocess as sp
import vhpi.api.logging as log
from vhpi.api.logging import job_out_msg
from vhpi.api.types import Job
import vhpi.constants as const


def log_cfg_type_err(item, type_):
    log.error(f'Type Error in config file. "{item}" must be of type {type_}.')


def log_cfg_no_absolute_path_err(item):
    log.error(
        f'Value Error in config file. Please provide an absolute path for '
        f'"{item}".'
    )


def is_machine_online(source_ip):
    """"""
    try:
        sp.check_output(["ping", "-c", "1", source_ip])
        return True

    except sp.CalledProcessError:
        return False


def validate_machine_is_online(source_ip, init_time):
    if not is_machine_online(source_ip):
        log.info(
            f'    Error: Source went offline: '
            f'{time.strftime(const.TIMESTAMP_FORMAT)}'
        )
        log.error(job_out_msg(2, init_time))
        return False
    return True


def validate_backup_src(backup_src, init_time):
    if not os.path.exists(backup_src):
        log.critical(
            f'    Error: Backup source does not exist.": '
            f'{backup_src}'
        )
        log.error(job_out_msg(2, init_time))
        return False
    return True


def validate_backup_dst(backup_dst, init_time):
    if not os.path.isdir(backup_dst):
        log.critical(
            f'    Error: Invalid Destination: {backup_dst}'
        )
        log.error(job_out_msg(2, init_time))
        return False
    return True


def initial_app_validation_routine(cfg: dict):
    """
    Test if minim required items are available for vhpi to run.
    """
    if not cfg:
        log.critical(
            'Invalid config file.\n'
            'Please provide a valid config file at the default location: '
            '"~/.config/vhpi/vhpi_cfg.yaml" or provide a custom path via '
            '--config option.'
        )
        sys.exit(1)


def initial_job_validation_routine(
    job_cfg: dict,
    init_time: int,
):
    """
    These checks are run directly on the cfg data, before the Job object is
    created.
    """
    backup_src = job_cfg.get('rsync_src')
    backup_dst = job_cfg.get('rsync_dst')

    if not type(backup_src) == str:
        log_cfg_type_err('rsync_src', 'string')
        return False

    if not type(backup_dst) == str:
        log_cfg_type_err('rsync_dst', 'string')
        return False

    if not backup_src[0] in ['/']:
        log_cfg_no_absolute_path_err('rsync_src')
        return False

    if not backup_dst[0] in ['/']:
        log_cfg_no_absolute_path_err('rsync_dst')
        return False

    if not validate_backup_src(backup_src, init_time):
        return False

    if not validate_backup_dst(backup_dst, init_time):
        return False

    return True


def rsync_monitor_routine(job: Job):
    """"""
    result = True

    if not validate_backup_src(job.backup_src, job.init_time):
        result = False

    if not validate_backup_dst(job.backup_root, job.init_time):
        result = False

    if not validate_machine_is_online(job.source_ip, job.init_time):
        result = False

    return result


def run_rsync_monitor(job: Job, sub_process: sp.Popen):
    """"""
    duration = 1

    while True:
        # break if subprocess finished.
        if sub_process.poll() is not None:
            break

        if not rsync_monitor_routine(job):
            # terminate/kill sp if routine fails and sp still running.
            if sub_process.poll() is None:
                sub_process.terminate()
                if sub_process.poll() is None:
                    sub_process.kill()
            break

        duration = duration if duration >= 60 else duration * 2
        time.sleep(duration)
