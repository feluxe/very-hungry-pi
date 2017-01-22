#!/usr/bin/env python3

# Copyright (C) 2016 Felix Meyer-Wolters
#
# This file is part of 'Very Hungry Pi' (vhpi) - An application to create backups.
#
# 'Very Hungry Pi' is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
vhpi.utils
~~~~~~~~~~~~~~
This module provides utility functions that are used within vhpi
that are also useful for external consumption.
"""

import os
import yaml


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


# load Yaml
def load_yaml(file):
    with open(file, 'r') as stream:
        return yaml.safe_load(stream)
