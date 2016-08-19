#!/usr/bin/env python3

import os


class Settings(object):
    home = os.path.expanduser("~")
    cfg_dir = home + '/.very_hungry_pi'
    cfg_file = cfg_dir + '/config.yaml'
    log_cfg = cfg_dir + '/log_config.yaml'
    lock_file = cfg_dir + '/lock'
    validation_file = '.backup_valid'
    timestamp_file = '.backup_timestamps'
    timestamp_format = '%Y-%m-%d %H:%M:%S'
    jobs_cfg = None
    exclude_lib = None
    intervals = None
