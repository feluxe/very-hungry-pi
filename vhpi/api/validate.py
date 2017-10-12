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


def is_machine_online(source_ip: str) -> bool:
    """"""
    try:
        sp.check_output(["ping", "-c", "1", source_ip])
        return True

    except sp.CalledProcessError:
        return False


def backup_src_exists(src: str) -> bool:
    return os.path.exists(src)


def backup_dst_is_dir(dst: str) -> bool:
    return os.path.isdir(dst)
