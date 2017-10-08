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

import os
import vhpi.constants as const


def ensure_dir(cfg_dir: str):
    """Create app cfg dir if not exist."""
    os.makedirs(cfg_dir, exist_ok=True)


def ensure_file(file: str):
    """Create a file if it does not exist."""
    open(file, 'a').close()


# Init app constants.
const.init_default_constants()

# Make sure default config files exist.
ensure_dir(const.APP_CFG_DIR)
ensure_file(const.USER_CFG_FILE)

__author__ = "Felix Meyer-Wolters"
__license__ = "GPL-3.0"
__version__ = const.VERSION
