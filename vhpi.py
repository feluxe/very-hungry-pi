#!/usr/bin/env python3

import os
import time
import datetime
import subprocess
import glob
import logging
import logging.config
import sys
import fcntl
import yaml
import threading
import signal

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
        self.rsync_process = None
        self.t = None

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

    # Check if source is online repeatedly. If it goes offline exit program.
    def machine_watcher(self, ip, t):
        time.sleep(5)  # Wait for rsync to run.
        while self.rsync_process:
            if not is_machine_online(ip):
                log.info('    Error: Source went offline: ' +
                         time.strftime('%Y-%m-%d %H:%M:%S'))
                log.job_out(2, t)
                self.rsync_process.kill()
                sys.exit()
            time.sleep(60)

    # execute rsync command.
    def exec_rsync(self, _command):
        log.debug_ts_msg('Start: rsync execution.')
        return_val = True
        try:
            log.info('    Executing: ' + ' '.join(_command))
            self.rsync_process = subprocess.Popen(_command,
                                                  shell=False,
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.STDOUT,
                                                  close_fds=True,
                                                  universal_newlines=True)
            output = self.rsync_process.stdout.read()
            log.debug(output)
            log.if_in_line('warning', 'rsync: ', output)
            log.if_in_line('warning', 'rsync error: ', output)
            log.if_in_line('info', 'bytes/sec', output)
            log.if_in_line('info', 'total size is ', output)
        except (subprocess.SubprocessError, subprocess.CalledProcessError) as _e:
            if _e.returncode and _e.returncode != 23:
                log.warning('    Error: Unknown Rsync Exit Code')
                return_val = False
        self.rsync_process = None
        log.debug_ts_msg('End: rsync execution.')
        return return_val


class Log(object):
    def __init__(self, name):
        self.name = name
        self.logger = self.init_logger(self.name)

    # Load log cfg file and initiate logging system.
    # Add functions to 'logging' class.
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
        logging.Logger.debug_ts_msg = self.debug_ts_msg
        return logging.getLogger(name)

    # Filter a string for words. Each line that contains a word will be logged.
    # Can be used on the output of rsync to log each line with an 'error' or 'warning'.
    def matching_lines(self, level, needle, lines):
        lines = lines.splitlines()
        matches = ['    ' + level.title() + ': ' + s
                   for s in lines if needle in s]
        matches_str = '\n'.join(matches)
        dynamic_func = getattr(self.logger, level)
        dynamic_func(matches_str)

    # Log message used when a job ends.
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

    def debug_ts_msg(self, message=''):
        self.logger.debug('    ' + time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + message)


# Kill Sequence


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
    file_dir = os.path.dirname(file)
    if not check_path(file_dir) == 'dir':
        log.critical('    Error: Could not find dir :' + file_dir)
        sys.exit()
    try:
        with open(file, 'r') as stream:
            output = yaml.safe_load(stream)
    except FileNotFoundError:
        if not create_new:
            log.critical('    Error: Could not read file :' + file)
            sys.exit()
        output = open(file, 'w+')
    except IOError as _e:
        log.critical('    Error: Could not read YAML file.', _e)
        sys.exit()
    except yaml.YAMLError as _e:
        log.critical("    Error: Error in YAML file:", _e)
        sys.exit()
    return output


# Write Yaml
def write_yaml(data, file):
    try:
        with open(file, 'w') as outfile:
            outfile.write(yaml.dump(data, default_flow_style=True))
    except IOError as e:
        log.error('    Error: Could not write to YAML file.', e)
        sys.exit()
    except yaml.YAMLError as _e:
        log.error("    Error writing YAML file:", _e)
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
    timestamp = time.mktime(datetime.datetime.strptime(timestamp, _format).timetuple())
    time_now = int(time.time())
    if time_now - cycle_time >= timestamp:
        return True
    else:
        return False


# Check if path exists and return (file|dir| false).
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


# # Increase the dir number by one for each due snapshot.
# # In order to know which dirs need to be changed, the function iterates through
# # the keep-amount that is set by the user.
# # If a dir does not exist, it is skipped.
# # Returns all jobs that do not fail the shift.
# def shift_snaps_old(dest, due_snapshots, snapshots):
#     log.debug_ts_msg('Start: shift snapshots')
#     return_val = True
#     for snapshot in due_snapshots:
#         base_dir = clean_path(dest + '/' + snapshot + '.')
#         for num in range(snapshots[snapshot] - 1, -1, -1):
#             if check_path(base_dir + str(num)) == 'dir':
#                 try:
#                     log.debug_ts_msg('Shifting: ' + snapshot + str(num) + ' => ' + snapshot
#                                      + str(num + 1))
#                     os.rename(base_dir + str(num), base_dir + str(num + 1))
#                 except OSError as e:
#                     log.debug(_e)
#                     log.error('    Error: Could not rename dir: ' +
#                               base_dir + str(num)) + '==> ' + str(num + 1)
#                     log.error('    Error: Could not shift snapshot '
#                               'directories.')
#                     return_val = False
#     log.debug_ts_msg('End: shift snapshots')
#     return return_val


# Increase the dir num by one for selected snapshot type.
# Use the keep amount that is defined in config to find out how many dirs need to be changed.
def shift_snaps(dest, snapshot, snapshots):
    raw_path = clean_path(dest + '/' + snapshot + '.')
    for num in range(snapshots[snapshot] - 1, -1, -1):
        if check_path(raw_path + str(num)) == 'dir':
            try:
                os.rename(raw_path + str(num), raw_path + str(num + 1))
            except OSError as _e:
                log.debug(_e)
                log.critical('    Critical Error: Could not rename dir: '
                             + raw_path + str(num)) + '==> ' + str(num + 1)
                sys.exit()


def update_timestamp(dest, snapshot, timestamps):
    timestamps[snapshot] = time.strftime('%Y-%m-%d %H:%M:%S')
    write_yaml(timestamps, clean_path(dest + '/' + TIMESTAMP_FILE))


# Create hardlinks from 'backup.latest' to each queried
#   snapshot dir. E.g. 'hourly.0', 'weekly.0', ...
def make_snapshots(dest, due_snapshots, snapshots):
    log.debug_ts_msg('Start: make snapshots.')
    return_val = True
    for snapshot in due_snapshots:
        source = clean_path(dest + '/backup.latest')
        destination = clean_path(dest + '/' + snapshot + '.0.incomplete')
        try:
            log.debug_ts_msg('Making links from: ' + source + ' to ' + snapshot + '.0')
            subprocess.check_output(['rm', '-rf', destination])
            subprocess.check_output(['cp', '-al', source, destination])
            time.sleep(3)
            shift_snaps(dest, snapshot, snapshots)
            time.sleep(3)
            # remove '.incomplete' label from destination dir name.
            subprocess.check_output(['mv', destination, destination.replace('.incomplete', '')])
            update_timestamp(dest, snapshot, snapshots)
        except subprocess.CalledProcessError as _e:
            log.debug(_e)
            log.error('    Error: Could not make hardlinks for: ' + dest)
            return_val = False
            continue
    log.debug_ts_msg('End: make snapshots.')
    return return_val


# Delete all folders that are out of keep range.
# These are the snapshot folders that contain states that are
#   older than what the user likes to keep.
# The range is defined in config.
def del_deprecated_snaps(deprecated_dirs):
    log.debug_ts_msg('Start: delete deprecated snapshots.')
    return_val = True
    for _dir in deprecated_dirs:
        log.debug_ts_msg('Deleting dir: ' + _dir)
        if check_path(_dir):
            try:
                subprocess.check_output(['rm', '-rf', str(_dir)])
            except subprocess.CalledProcessError as e:
                log.debug(_e)
                log.error('    Error: Could not delete deprecated snapshot ' + _dir)
                return_val = False
    log.debug_ts_msg('End: delete deprecated snapshots.')
    return return_val


def main():
    cfg_data = load_yaml(CFG)
    app = App(cfg_data)

    # Loop through each job that is defined in the cfg.
    for _id, job_cfg in enumerate(app.jobs):

        job = Job(_id, job_cfg, app)  # Create job instance with job config data.
        job.t = time.time()  # set initial timestamp

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
            log.job_out(2, job.t)
            continue

        if not job.check_dest(job.dest):
            log.job_out(2, job.t)
            continue

        # Start a watcher in a thread which checks if source machine is online each 60s.
        t_machine_watcher = threading.Thread(target=job.machine_watcher, args=(job.src_ip, job.t))
        t_machine_watcher.setDaemon(True)
        t_machine_watcher.start()

        if not job.exec_rsync(job.rsync_command):
            log.job_out(2, job.t)
            continue

        if not del_deprecated_snaps(job.deprecated_dirs):
            log.job_out(2, job.t)
            continue

        if not make_snapshots(job.dest, job.due_snapshots, job.snapshots):
            log.job_out(2, job.t)
            continue

        log.job_out(0, job.t)


if __name__ == "__main__":
    log = Log('main')
    log = log.logger
    lock = check_lock(LOCK_FILE)
    os.setpgrp()  # create new process group, become its leader. os.killpg will kill all processes.
    try:
        main()
    except KeyboardInterrupt:
        log.error('    Error: Backup aborted by user.')
        log.job_out(2, time.time())
        os.killpg(0, signal.SIGKILL)  # kill all processes in my group
    except Exception as _e:
        log.error('    Error: An Exception was thrown: ')
        log.error(_e)
        os.killpg(0, signal.SIGKILL)  # kill all processes in my group
        log.job_out(2, time.time())
