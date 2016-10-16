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


# This module contains universally needed functions.

import os
import sys
import yaml

from .logger import log
from .processes import Processes


# load Yaml
def load_yaml(file, create_new=False):
    output = None
    try:
        with open(file, 'r') as stream:
            output = yaml.safe_load(stream)
    except FileNotFoundError:
        if not create_new:
            log.critical('    Error: Could not find YAML file :' + file)
            exit_main()
        output = open(file, 'w+')
    except IOError as e:
        log.critical('    Error: Could not read YAML file.', e)
        exit_main()
    except yaml.YAMLError as e:
        log.critical("    Error: Error in YAML file:", e)
        exit_main()
    return output


# Write Yaml
def write_yaml(data, file):
    try:
        with open(file, 'w') as outfile:
            outfile.write(yaml.dump(data, default_flow_style=True))
    except IOError as e:
        log.error('    Error: Could not write to YAML file.', e)
        exit_main()
    except yaml.YAMLError as e:
        log.error("    Error writing YAML file:", e)
        exit_main()
    return True


def clean_path(_path):
    return _path.replace('//', '/')


# Check if path exists and return (file|dir|false).
def check_path(path):
    if not os.path.exists(path):
        return False
    else:
        if os.path.isfile(path):
            return "file"
        elif os.path.isdir(path):
            return "dir"
        else:
            return False


def kill_processes():
    if Processes.rsync:
        log.debug('    Info: Killing rsync process.')
        Processes.rsync.kill()
        Processes.rsync = None
    if Processes.cp:
        log.debug('    Info: Killing cp process.')
        Processes.cp.kill()
        Processes.cp = None


def exit_main():
    kill_processes()
    sys.exit()
