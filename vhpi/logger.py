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


import logging
import logging.config
import yaml
import time

from .settings import Settings as S


class Log(object):
    def __init__(self, name):
        self.logger = self.init_logger(name)

    # Load log cfg file and initiate logging system.
    # Add functions to 'logging' class.
    def init_logger(self, name):
        content = ''
        with open(S.log_cfg, 'r') as stream:
            for line in stream:
                content += line.replace('~', S.home)
            log_cfg = yaml.safe_load(content)
        logging.config.dictConfig(log_cfg)
        logging.Logger.if_in_line = self.matching_lines
        logging.Logger.job_out = self.job_out
        logging.Logger.debug_ts_msg = self.debug_ts_msg
        logging.Logger.skip_msg = self.skip_msg
        logging.Logger.job_in = self.job_in
        return logging.getLogger(name)

    # Filter a string for words. Each line that contains a word will be logged.
    # Can be used on the output of rsync to log each line with an 'error' or 'warning'.
    def matching_lines(self, level, needle, lines):
        lines = lines.splitlines()
        matches = ['    ' + level.title() + ': ' + s
                   for s in lines if needle in s]
        matches_str = '\n'.join(matches)
        dynamic_func = getattr(self.logger, level)
        dynamic_func(matches_str) if len(matches) > 0 else None

    def job_in(self, ip, src, due_snapshots):
        log_msg = ' [Executing] ' + ip + '\t' + src + '\n'
        self.logger.info(time.strftime(S.timestamp_format) + log_msg)
        self.logger.info('    Due: ' + ', '.join(due_snapshots))

    # Log message used when a job ends.
    def job_out(self, code, _t, message=''):
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
            new_msg += '[Unknown job termination] after: ' + duration + ' (h:m:s)' + message
        self.logger.info(time.strftime(S.timestamp_format) + ' ' + new_msg)

    def debug_ts_msg(self, message=''):
        self.logger.debug('    ' + time.strftime(S.timestamp_format) + ' ' + message)

    def skip_msg(self, online, due_jobs, ip, path):
        ip = fixed_str_len(ip, 15, ' ') + '  '
        path = '[' + fixed_str_len(path, 50, '·') + ']  '
        online = 'online' if online else 'offline'
        online = 'Source ' + fixed_str_len(online, 7, ' ') + ' | '
        due_jobs_sorted = due_jobs if len(due_jobs) <= 1 else due_jobs.sort()
        due = 'Due: ' + ', '.join(due_jobs_sorted) + '\t' if due_jobs else 'No due jobs\t'
        msg = '[Skipped] ' + ip + path + online + due
        self.logger.info(time.strftime(S.timestamp_format) + ' ' + msg)


def fixed_str_len(_str, limit, symbol):
    output = ''
    if len(_str) == limit:
        output = _str
    elif len(_str) > limit:
        hl = int(limit / 2)
        output = _str.replace(_str[hl - 3:(hl - 2) * -1], '[...]')
    elif len(_str) < limit:
        output = _str + (symbol * (limit - len(_str)))
    return output


log = Log('main')
log = log.logger
