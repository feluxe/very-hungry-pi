#!/usr/bin/env python3

import os
import time
import datetime
import shutil
import subprocess
import glob
import logging
import logging.config
import sys
import fcntl
import yaml


HOME = os.path.expanduser("~")
CFG_DIR = HOME + '/.very_hungry_pi'
CFG = CFG_DIR + '/config.yaml'
LOG_CFG = CFG_DIR + '/log_config.yaml'
LOCK_FILE = CFG_DIR + '/lock'
VALID_FILE = '.backup_valid'
TIMESTAMP_FILE = '.backup_timestamps'


class App(object):

    def __init__(self, _cfg):
        self.jobs = _cfg['jobs_cfg']
        self.exclude_lib = _cfg['app_cfg']['exclude_lib']
        self.intervals = _cfg['app_cfg']['intervals']


class Job(object):

    def __init__(self, job_id, _job_cfg, _app):
        self.id = job_id
        self.src_ip = _job_cfg['source_ip']
        self.src = _job_cfg['rsync_src']
        self.dest = _job_cfg['rsync_dest']
        self.rsync_options = _job_cfg['rsync_options']
        self.excludes = self.get_excludes(_job_cfg['excludes'],
                                          _job_cfg['exclude_lists'],
                                          _app.exclude_lib)
        self.snapshots = _job_cfg['snapshots']
        self.timestamps = self.get_timestamps(self.dest, _app.intervals)
        self.due_snapshots = self.get_due_snapshots(self.snapshots,
                                                    self.timestamps,
                                                    _app.intervals)
        self.rsync_command = self.build_rsync_command(self.rsync_options,
                                                      self.excludes,
                                                      self.src,
                                                      self.dest)
        self.deprecated_dirs = self.get_deprecated_dirs(self.dest,
                                                        self.snapshots)

    @staticmethod
    def get_timestamps(dest, intervals):
        timestamps = load_yaml(clean_path(dest + '/' + TIMESTAMP_FILE), True)
        if type(timestamps) is not dict:
            timestamps = {}
        for interval in intervals:
            if interval not in timestamps:
                timestamps.update({interval: 0})
        return timestamps

    @staticmethod
    # Get due Snapshots
    def get_due_snapshots(_snapshots, timestamps, intervals):
        due = [interval for interval in _snapshots
               if _snapshots[interval] and
               is_due(interval, intervals, timestamps[interval])]
        return due

    @staticmethod
    def check_valid_file(src):
        v_file_path = clean_path(src + "/" + VALID_FILE)
        if not check_path(v_file_path) == 'file':
            log.error('    Error: Could not validate source via '
                      '"validation file"' + v_file_path)
            return False
        return True

    @staticmethod
    def check_dest(dest):
        if not check_path(dest) == 'dir':
            log.error('    Error: Invalid Destination:' + dest)
            return False
        return True

    @staticmethod
    def get_excludes(excludes, excl_lists, excl_lib):
        for _list in excl_lists:
            for item in excl_lib[_list]:
                excludes.append(item)
        return excludes

    # build rsync command for subprocess module.
    @staticmethod
    def build_rsync_command(options, excludes, src, dest):
        options = options.split()
        excludes = ['--exclude=' + item for item in excludes]
        src = clean_path(src)
        dest = clean_path(dest + '/backup.latest')
        return ['rsync'] + options + excludes + [src, dest]

    @staticmethod
    def get_deprecated_dirs(dest, due_snapshots):
        deprecated = []
        for snapshot in due_snapshots:
            base_dir = clean_path(dest + '/' + snapshot + ".")
            keep_range = range(due_snapshots[snapshot] - 2, -1, -1)
            active = [base_dir + str(num) for num in keep_range]
            deprecated.extend([_dir for _dir in glob.glob(base_dir + '*')
                               if _dir not in active])
        return deprecated


class Log(object):

    def __init__(self, name):
        self.name = name
        self.logger = self.init_logger(self.name)

    def init_logger(self, name):
        content = ''
        with open(LOG_CFG, 'r') as stream:
            for line in stream:
                content += line.replace('~', HOME)
            log_cfg = yaml.safe_load(content)
        logging.config.dictConfig(log_cfg)
        logging.Logger.if_in_line = self.matching_lines
        logging.Logger.job_out = self.job_out
        logging.Logger.out_line = self.out_line
        return logging.getLogger(name)

    def matching_lines(self, level, needle, lines):
        lines = lines.splitlines()
        matches = ['    ' + level.title() + ': ' + s
                   for s in lines if needle in s]
        matches_str = '\n'.join(matches)
        dynamic_func = getattr(self.logger, level)
        dynamic_func(matches_str)

    def job_out(self, code, _t):
        seconds = time.time() - _t
        duration = time.strftime('%H:%M:%S', time.gmtime(seconds))
        message = '    '
        if code == 0:
            message += '[Completed] after: ' + duration + ' (h:m:s)'
        elif code == 1:
            message += '[Skipped]'
        else:
            message += '[Failed] after: ' + duration + ' (h:m:s)'
        self.logger.info(message + '\n')

    def out_line(self, messages):
        messages = '; '.join(messages)
        self.logger.info(time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + messages)


# check if machine is online.
def is_machine_online(ip):
    ping_command = ["ping", "-c", "1", ip]
    try:
        subprocess.check_output(ping_command)
        return True
    except subprocess.CalledProcessError:
        return False


# Check if another instance of the script is already running. If so exit.
def check_lock(lockfile):
    try:
        lockfile = open(lockfile, 'w')
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.info('    Info: Another instance of this Script was executed, '
                 'but it was blocked successfully. ' +
                 time.strftime('%Y-%m-%d %H:%M:%S'))
        sys.exit()
    return lockfile


# load Yaml
def load_yaml(file, create_new=False):
    try:
        with open(file, 'r') as stream:
            output = yaml.safe_load(stream)
    except FileNotFoundError:
        if not create_new:
            log.critical('    Error: Could not read file :' + file)
            sys.exit()
        output = open(file, 'w+')
    except IOError as e:
        log.critical('    Error: Could not read YAML file.', e)
        sys.exit()
    except yaml.YAMLError as e:
        log.critical("    Error: Error in YAML file:", e)
        sys.exit()
    return output


# Write Yaml
def write_yaml(data, file):
    try:
        with open(file, 'w') as outfile:
            outfile.write(yaml.dump(data, default_flow_style=True))
    except IOError:
        log.error('    Error: Could not write to YAML file.')
        sys.exit()
    except yaml.YAMLError as e:
        log.error("    Error writing YAML file:", e)
        sys.exit()
    return True


def clean_path(_path):
    return _path.replace('//', '/')


# Determine if a snapshot is due.
def is_due(_type, intervals, timestamp):
    if _type not in intervals:
        log.critical("    Critical: No time interval set for type: " + _type)
        sys.exit()
    cycle_time = intervals[_type]
    if timestamp == 0 or timestamp == '0' or timestamp == '':
        timestamp = '1970-01-01 00:00:00'
    _format = "%Y-%m-%d %H:%M:%S"
    timestamp = time.mktime(datetime.datetime.strptime(timestamp,
                                                       _format).timetuple())
    time_now = int(time.time())

    if time_now - cycle_time >= timestamp:
        return True
    else:
        return False


# func: check if path exists and return type (file|dir).
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


# execute rsync command.
def exec_rsync(_command):
    try:
        log.info('    Executing: ' + ' '.join(_command))
        p = subprocess.Popen(_command,
                             shell=False,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             close_fds=True,
                             universal_newlines=True)
        output = p.stdout.read()
        log.debug(output)
        log.if_in_line('warning', 'rsync: ', output)
        log.if_in_line('warning', 'rsync error: ', output)
        log.if_in_line('info', 'bytes/sec', output)
        log.if_in_line('info', 'total size is ', output)
    except (subprocess.SubprocessError, subprocess.CalledProcessError) as e:
        if e.returncode and e.returncode != 23:
            log.warning('    Error: Unknown Rsync Exit Code')
            return False
    return True


# Increase the dir number by one for each due snapshot.
# In order to know which dirs need to be changed, the function iterates through
# the keep-amount that is set by the user.
# If a dir does not exist, it is skipped.
# Returns all jobs that do not fail the shift.
def shift_snaps(dest, due_snapshots, snapshots):
    for snapshot in due_snapshots:
        base_dir = clean_path(dest + '/' + snapshot + '.')
        for num in range(snapshots[snapshot] - 1, -1, -1):
            if check_path(base_dir + str(num)) == 'dir':
                try:
                    os.rename(base_dir + str(num), base_dir + str(num + 1))
                except OSError as e:
                    log.debug(e)
                    log.error('    Error: Could not rename dir: ' +
                              base_dir + str(num)) + '==> ' + str(num + 1)
                    log.error('    Error: Could not shift snapshot '
                              'directories.')
                    return False
    return True


def make_hard_links(dest, due_snapshots):
    for snapshot in due_snapshots:
        source = clean_path(dest + '/backup.latest')
        destination = clean_path(dest + '/' + snapshot + '.0')
        try:
            subprocess.check_output(['cp', '-al', source, destination])
        except subprocess.CalledProcessError as e:
            log.debug(e)
            log.error('    Error: Could not make hardlinks for: ' + dest)
            return False
    return True


def del_deprecated_snaps(deprecated_dirs):
    for _dir in deprecated_dirs:
        if not check_path(_dir) == False:
            try:
                shutil.rmtree(str(_dir))
            except OSError as e:
                log.debug(e)
                log.error('    Error: Could not delete deprecated snapshot ' +
                          _dir)
                return False
    return True


def update_timestamps(dest, due_snapshots, timestamps):
    for snapshot in due_snapshots:
        timestamps[snapshot] = time.strftime('%Y-%m-%d %H:%M:%S')
        write_yaml(timestamps, clean_path(dest + '/' + TIMESTAMP_FILE))
    return True


def main():

    cfg_data = load_yaml(CFG)
    app = App(cfg_data)

    for _id, job_cfg in enumerate(app.jobs):

        job = Job(_id, job_cfg, app)
        t = time.time()

        if not job.due_snapshots:
            log.out_line(['[Skipped] No dues for: ' + job.src])
            continue

        if not is_machine_online(job.src_ip):
            i1 = '[Skipped] Source offline: ' + job.src_ip
            i2 = 'Due: ' + ', '.join(job.due_snapshots)
            log.out_line([i1, i2])
            continue

        log.info(time.strftime('%Y-%m-%d %H:%M:%S') + ' [Executing] ' +
                 job.src + '\n')
        log.info('    Due: ' + ', '.join(job.due_snapshots))

        if not job.check_valid_file(job.src):
            log.job_out(2, t)
            continue

        if not job.check_dest(job.dest):
            log.job_out(2, t)
            continue

        if not exec_rsync(job.rsync_command):
            log.job_out(2, t)
            continue

        if not del_deprecated_snaps(job.deprecated_dirs):
            log.job_out(2, t)
            continue

        if not shift_snaps(job.dest, job.due_snapshots, job.snapshots):
            log.job_out(2, t)
            continue

        if not make_hard_links(job.dest, job.due_snapshots):
            log.job_out(2, t)
            continue

        if not update_timestamps(job.dest, job.due_snapshots, job.timestamps):
            log.job_out(2, t)
            continue

        log.job_out(0, t)


if __name__ == "__main__":
    log = Log('main')
    log = log.logger
    lock = check_lock(LOCK_FILE)

    try:
        main()
    except KeyboardInterrupt:
        log.error('    Error: Backup aborted by user.')
        log.job_out(2, time.time())

