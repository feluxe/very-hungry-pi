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
import sys
from getpass import getpass
from typing import Any

import oyaml as yaml
from cryptography.fernet import Fernet

KEY = Fernet.generate_key()


def _encrypt(message: bytes) -> bytes:
    return Fernet(KEY).encrypt(message)


def _decrypt(token: bytes) -> bytes:
    return Fernet(KEY).decrypt(token)


def write_login(login_name):
    """Encrypt user input for ssh login."""
    return _encrypt(
        getpass(f"\nEnter pw for {login_name.split(':')[0]}:\n").strip().encode()
    )


def read_login(token):
    """Decrypt user input for ssh login."""
    return _decrypt(token).decode().strip()


def is_machine_online(source_ip: str) -> bool:
    """Check if a machine is running via 'ping'"""
    try:
        sp.check_output(["ping", "-c", "1", source_ip])
        return True

    except sp.CalledProcessError:
        return False


def clean_path(_path):
    """Remove double slashes"""
    return _path.replace("//", "/")


def check_path_type(path):
    """
    Check if path is 'file' | 'dir' | False
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
    with open(file, "r") as f:
        return yaml.safe_load(f)


def save_yaml(data: Any, file: str, default_style: str = '"') -> None:
    """
    Save data to yaml file.
    """
    with open(file, "w") as yaml_file:
        yaml.dump(data, yaml_file, default_style=default_style)


def eprint(*objects, sep=" ", end="\n", file=sys.stderr, flush=False) -> None:
    """
    Write to sdterr.
    """
    print(*objects, sep=sep, end=end, file=file, flush=flush)
