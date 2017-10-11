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
from vhpi.utils import eprint
from pkg_resources import get_distribution, DistributionNotFound, \
    VersionConflict


def _get_version() -> str:
    try:
        version: str = get_distribution('vhpi').version or 'none'

    except DistributionNotFound or VersionConflict:
        eprint('No version info available.')
        version: str = 'none'

    return version


def set_cfg_dir(custom_dir: str):
    global APP_CFG_DIR, USER_CFG_FILE

    APP_CFG_DIR = custom_dir
    USER_CFG_FILE = f'{APP_CFG_DIR}/vhpi_cfg.yaml'


def init_default_constants() -> None:
    """
    Initiate the default constants that are used by the APP/API.
    These cannot be changed by the user cfg.
    """
    global VERSION, HOME_DIR, APP_ROOT_DIR, APP_CFG_DIR, USER_CFG_FILE

    VERSION = _get_version()
    HOME_DIR = os.path.expanduser('~')
    APP_ROOT_DIR = os.path.dirname(__file__)
    APP_CFG_DIR = HOME_DIR + '/.config/vhpi'
    USER_CFG_FILE = APP_CFG_DIR + '/vhpi_cfg.yaml'


VERSION = None
HOME_DIR = None
APP_ROOT_DIR = None
APP_CFG_DIR = None
USER_CFG_FILE = None
TIMESTAMP_FILE_NAME = '.backup_timestamps'
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
