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

import sys
import fcntl
from vhpi.api import job
from vhpi.api.types import Settings
import vhpi.constants as const
import vhpi.api.logging as log


def _check_lock(lockfile: str):
    """
    Check if another instance of the script is already running by using the
    'flock' mechanism. If another instance is already running: exit app.
    """
    try:
        lockfile = open(lockfile, 'w')
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

    except BlockingIOError:
        log.debug(log.lvl1.ts_msg(
            'Info: Another instance of vhpi was executed and blocked '
            'successfully.'
        ))
        sys.exit(0)

    return lockfile


def _initial_app_validation_routine(cfg: dict) -> None:
    """
    These checks are to validate the user config (app_cfg part).
    You may only use lvl0 log output here.
    """
    if not cfg:
        log.critical(
            'Invalid config file.\n'
            'Please provide a valid config file at the default location: '
            '"~/.config/vhpi/vhpi_cfg.yaml" or provide a custom path via '
            '--config option.'
        )
        sys.exit(1)


def run(cfg: dict):
    """"""
    lock: str = _check_lock(f'{const.APP_CFG_DIR}/lock')

    _initial_app_validation_routine(cfg)

    settings = Settings(
        exclude_lib=cfg.get('app_cfg').get('exclude_lib'),
        intervals=cfg.get('app_cfg').get('intervals'),
    )

    for job_cfg in cfg['jobs']:
        job.run(job_cfg, settings)
