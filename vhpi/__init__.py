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
import vhpi.constants as const
from pkg_resources import resource_filename


def _ensure_dir(cfg_dir: str):
    """Create app cfg dir if not exist."""
    os.makedirs(cfg_dir, exist_ok=True)


def _create_config(default_cfg_file):
    """Create a file if it does not exist."""
    example_cfg: str = os.path.abspath(
        resource_filename('vhpi.examples', 'vhpi_cfg.yaml'))

    with open(example_cfg, 'r') as src_file:
        with open(default_cfg_file, 'w') as dst_file:
            dst_file.write(src_file.read())


# Init app constants.
const.init_default_constants()

_ensure_dir(const.APP_CFG_DIR)

# Make sure default config files exist.
if not os.path.isfile(const.USER_CFG_FILE):
    _create_config(const.USER_CFG_FILE)

__author__ = "Felix Meyer-Wolters"
__license__ = "GPL-3.0"
__version__ = const.VERSION
