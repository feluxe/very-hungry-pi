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
vhpi.logging
~~~~~~~~~~~~~~

This module contains vhpi's handler for python's logging module.
"""

import logging
import logging.config
import yaml
import time
from math import ceil
from os.path import expanduser

timestamp_format = '%Y-%m-%d %H:%M:%S'
home_dir = expanduser("~")
log_cfg = home_dir + '/.very_hungry_pi/log_config.yaml'


class VhpiLogger(object):
    """
    This Class is a wrapper for the Pythons logging module.
    It adds some more functions to the logging.Logger class.
    A config is loaded on initialization and a logger instance is created.
    """

    def __init__(self, name):
        self.set_log_config()
        self.add_log_methods()
        self.logger = logging.getLogger(name)

    def set_log_config(self):
        global log_cfg
        global home_dir
        content = ''
        with open(log_cfg, 'r') as stream:
            for line in stream:
                content += line.replace('~', home_dir)
            log_cfg = yaml.safe_load(content)
        logging.config.dictConfig(log_cfg)

    def add_log_methods(self):
        """Add functions to Logger class"""
        logging.Logger.if_in_line = self.matching_lines
        logging.Logger.job_out = self.job_out
        logging.Logger.skip_msg = self.skip_msg
        logging.Logger.job_in = self.job_in

    def matching_lines(self, level, needle, lines):
        """Filter a multi-line string for words.
        Each line that contains a word will be logged.
        Can be used on the output of rsync to log each line with an 'error' or 'warning'.
        :param level:
        :param needle:
        :param lines:
        """
        lines = lines.splitlines()
        matches = ['    ' + level.title() + ': ' + s
                   for s in lines if needle in s]
        matches_str = '\n'.join(matches)
        dynamic_func = getattr(self.logger, level)
        dynamic_func(matches_str) if len(matches) > 0 else None

    def job_in(self, ip, src, due_snapshots):
        """Log message for starting a new backup job"""
        log_msg = ' [Executing] ' + ip + '\t' + src + '\n'
        self.logger.info(time.strftime(timestamp_format) + log_msg)
        self.logger.info('    Due: ' + ', '.join(due_snapshots))

    def job_out(self, code, _t, message=''):
        """Log message used when a job ends."""
        seconds = time.time() - _t
        duration = time.strftime('%H:%M:%S', time.gmtime(seconds))
        new_msg = ''
        if code == 0:
            new_msg += '[Completed] after: ' + duration + ' (h:m:s)' + message
        elif code == 1:
            new_msg += '[Skipped] ' + message
        elif code == 2:
            new_msg += '[Failed] after: ' + duration + ' (h:m:s)' + message
        else:
            new_msg += '[Job Result Unknown] after: ' + duration + ' (h:m:s)' + message
        self.logger.info('\n' + time.strftime(timestamp_format) + ' ' + new_msg)

    def skip_msg(self, online, due_jobs, ip, path):
        """Log message for Skipping a backup."""
        ip = fix_str_len(ip, 15, ' ') + '  '
        path = '[' + fix_str_len(path, 50, '·') + ']  '
        online = 'online' if online else 'offline'
        online = 'Source ' + fix_str_len(online, 7, ' ') + ' | '
        due_jobs_sorted = due_jobs if len(due_jobs) <= 1 else due_jobs.sort()
        due = 'Due: ' + ', '.join(due_jobs_sorted) + '\t' if due_jobs else 'No due jobs\t'

        msg = '[Skipped] ' + ip + path + online + due
        self.logger.info(time.strftime(timestamp_format) + ' ' + msg)


def ts_msg(ind=4, msg=''):
    """Log a timestamp + message with log level (info, debug, error, ...)."""
    return ind * ' ' + time.strftime(timestamp_format) + ' ' + msg


def fix_str_len(_str, limit, filler='.', rpl='[...]'):
    """
    Force a string to be of a certain length. E.g.:
    'Hello, I am [...] see you all!'  (Input str was longer than 30)
    'Ciao!.........................'  (Input str was shorter than 30)
    :param _str: input str.
    :param limit: whole number
    :param filler: The type of char that is used to fill gaps.
    :param rpl: A string that is  replacing the part of the input string which was cut out.
    :return A string that is exactly as long as param: limit.
    """
    output = ''
    str_len = len(_str)
    if str_len == limit:
        output = _str
    elif str_len > limit:
        cut_len = str_len + len(rpl) - limit
        slice_start = ceil((str_len - cut_len) / 2)
        slice_end = slice_start + cut_len
        output = _str.replace(_str[slice_start:slice_end], rpl) if cut_len <= str_len else rpl
        output = output[:limit - len(output)] if len(output) > limit else output
    elif str_len < limit:
        output = _str + (filler * (limit - str_len))
    return output


logger = VhpiLogger('main').logger
