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
Package Level Exceptions, Exception Raiser Functions and Exception Handlers.
"""

import sys
from typing import Callable
from vhpi.utils import eprint


def handler(func: Callable, kwargs=dict) -> None:
    try:
        func(**kwargs)
        sys.exit(0)

    except KeyboardInterrupt:
        eprint('\nScript aborted by user. (KeyboardInterrupt)')
        sys.exit(1)
