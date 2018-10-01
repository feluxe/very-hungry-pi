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
import sys
import oyaml as yaml
from typing import Any


def clean_path(_path):
    """Remove double slashes"""
    return _path.replace('//', '/')


def check_path(path):
    """Check if path is:
    :return 'file' | 'dir' | False
    """
    if not os.path.exists(path):
        return False
    else:
        if os.path.isfile(path):
            return "file"
        elif os.path.isdir(path):
            return "dir"
        else:
            return False


def load_yaml(file: str) -> dict:
    """
    Load yaml file.
    """
    with open(file, 'r') as f:
        return yaml.safe_load(f)


def save_yaml(data: Any, file: str, default_style: str = '"') -> None:
    """
    Save data to yaml file.
    """
    with open(file, 'w') as yaml_file:
        yaml.dump(data, yaml_file, default_style=default_style)


def eprint(*objects, sep=' ', end='\n', file=sys.stderr, flush=False) -> None:
    print(*objects, sep=sep, end=end, file=file, flush=flush)
