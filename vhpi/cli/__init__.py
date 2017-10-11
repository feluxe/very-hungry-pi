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

"""
The 'cli' package defines the Command Line Interface for vhpi.
It reads and parses the user input from the commandline and calls the
equivalent function from the 'api' package.
"""
import os
from docopt import docopt
from vhpi.api.main import run
from vhpi.utils import load_yaml
import vhpi.constants as const
import vhpi.api.logging as log


def _read_interface() -> str:
    return open(
        file=f'{os.path.dirname(__file__)}/interface.txt',
        mode='r'
    ).read()


def _get_user_input() -> dict:
    return docopt(
        doc=_read_interface(),
        version=const.VERSION
    )


def render(
    uinput: dict = _get_user_input(),
    cfg=None,
) -> None:
    """
    Execute command depending on user input.
    """

    # print(uinput)

    if uinput['--config']:
        const.set_cfg_dir(uinput['--config'])
        cfg = load_yaml(const.USER_CFG_FILE)
        log.init(const.APP_CFG_DIR)

    if uinput['run']:
        run(cfg=cfg)
