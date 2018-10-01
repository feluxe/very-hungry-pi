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
from vhpi import cli, exceptions
import vhpi.constants as const
import oyaml as yaml
import vhpi.api.logging as log


def load_user_cfg():
    """
    Load default user cfg files.
    """
    if os.path.isfile(const.USER_CFG_FILE):
        with open(const.USER_CFG_FILE, 'r') as f:
            return yaml.safe_load(f) or {}

    else:
        return {}


def execute() -> None:
    """"""
    log.init(const.APP_CFG_DIR)

    exceptions.handler(func=cli.render, kwargs={'cfg': load_user_cfg()})


if __name__ == '__main__':
    execute()
