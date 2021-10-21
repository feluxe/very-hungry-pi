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
 ╔══════════╗
 ║   vhpi   ║
 ╚══════════╝

Usage:
    vhpi run [options]
    vhpi -h | --help
    vhpi --version

Options:
    -c, --config-dir PATH             Set a custom config dir.
    -h, --help                        Show this screen.
        --version                     Show version.
"""

import fcntl
import os
import sys
import time
from typing import Any

import oyaml as yaml
from docopt import docopt
from pkg_resources import (
    DistributionNotFound,
    VersionConflict,
    get_distribution,
    resource_filename,
)

from . import job, lib
from .logging import log
from .types import App


def _load_user_cfg(user_cfg_file):
    if not os.path.isfile(user_cfg_file):
        log.critical(
            "Config File Missing.\n"
            + "Please provide a valid config file at the default location: \n"
            + user_cfg_file,
        )
        sys.exit(1)

    with open(user_cfg_file, "r") as f:
        return yaml.safe_load(f) or {}


def _get_version() -> str:
    try:
        return get_distribution("vhpi").version or "none"
    except (DistributionNotFound, VersionConflict):
        lib.eprint("No version info available.")
        return "none"


def _ensure_dir(cfg_dir: str):
    """
    Create dir if not exists.
    """
    os.makedirs(cfg_dir, exist_ok=True)


def _ensure_config(cfg_file):
    """
    Create a config file if it does not exist.
    """
    if not os.path.isfile(cfg_file):
        example_cfg: str = os.path.abspath(
            resource_filename("vhpi.examples", "vhpi_cfg.yaml")
        )

        with open(example_cfg, "r") as src_file:
            with open(cfg_file, "w") as dst_file:
                dst_file.write(src_file.read())


def get_app(args: dict[str, Any]) -> App:

    home_dir = os.path.expanduser("~")
    root_dir = os.path.dirname(__file__)
    cfg_dir = args["--config-dir"] or home_dir + "/.config/vhpi"
    cfg_file = cfg_dir + "/vhpi_cfg.yaml"
    log_dir = home_dir + "/vhpi_logs"

    _ensure_dir(cfg_dir)
    _ensure_dir(log_dir)
    _ensure_config(cfg_file)

    return App(
        version=_get_version(),
        home_dir=home_dir,
        root_dir=root_dir,
        cfg_dir=cfg_dir,
        cfg_file=cfg_file,
        log_dir=log_dir,
        timestamp_file_name=".backup_timestamps",
        timestamp_format="%Y-%m-%d %H:%M:%S",
    )


def _handle_exceptions(func, **kwargs):
    try:
        func(**kwargs)
    except KeyboardInterrupt:
        lib.eprint("\nScript aborted by user. (KeyboardInterrupt)")
        sys.exit(1)


def _handle_lock(lockfile: str, func, **kwargs):
    """
    Check if another instance of the script is already running by using the
    'flock' mechanism. If another instance is already running: exit app.
    """
    try:
        with open(lockfile, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            func(**kwargs)

    except BlockingIOError:
        log.debug(
            log.lvl1_ts_msg(
                "Info: Another instance of vhpi was executed and blocked "
                "successfully."
            )
        )
        sys.exit(0)


def run_backups(app: App):

    user_cfg_raw = _load_user_cfg(app.cfg_file)

    for job_raw in user_cfg_raw["jobs"]:
        rsync_src = job_raw.get("rsync_src", "")

        if ":" in rsync_src:
            job_raw["login_token"] = lib.write_login(rsync_src)
        else:
            job_raw["login_token"] = None

    while True:

        for job_raw in user_cfg_raw["jobs"]:
            job.run(app, job_raw, user_cfg_raw)

        time.sleep(10)


def startup() -> None:

    version = _get_version()
    args = docopt(doc=__doc__, version=version)
    app = get_app(args)

    # Init logger.
    log.update(app)

    if args.get("run"):
        _handle_exceptions(_handle_lock(f"{app.cfg_dir}/lock", run_backups, app=app))


if __name__ == "__main__":
    startup()
