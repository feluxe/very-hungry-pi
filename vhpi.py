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
        self.alive = True
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
        self.init_time = None
        self.rsync_process = None
        self.hardlink_process = None
        self.machine_watcher_thread = None

    @staticmethod
    def get_timestamps(dest, intervals):
        timestamps = load_yaml(clean_path(dest + '/' + TIMESTAMP_FILE), True)
        if type(timestamps) is not dict:
            timestamps = {}
        for interval in intervals:
            if interval not in timestamps:
                timestamps.update({interval: 0})
        return timestamps

    # Get due Snapshots
    def get_due_snapshots(self, _snapshots, timestamps, intervals):
        due = [interval for interval in _snapshots
               if _snapshots[interval] and
               self.is_due(interval, intervals, timestamps[interval])]
        return due

    def check_valid_file(self):
        v_file_path = clean_path(self.src + "/" + VALID_FILE)
        if not check_path(v_file_path) == 'file':
            log.error('    Error: Could not validate source via '
                      '"validation file"' + v_file_path)
            return False
        return True

    def check_dest(self):
        if not check_path(self.dest) == 'dir':
            log.error('    Error: Invalid Destination:' + self.dest)
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

    # check if machine is online.
    def is_machine_online(self):
        ping_command = ["ping", "-c", "1", self.src_ip]
        try:
            subprocess.check_output(ping_command)
            return True
        except subprocess.CalledProcessError:
            return False

    # Check if source is online repeatedly. If it goes offline exit program.
    def machine_watcher(self):
        time.sleep(5)  # Wait for rsync to run.
        while self.rsync_process:
            if not self.is_machine_online():
                log.info('    Error: Source went offline: ' +
                         time.strftime('%Y-%m-%d %H:%M:%S'))
                self.exit(2)
            time.sleep(60)

    # Start a watcher in a thread which checks if source machine is online each 60s.
    def start_machine_watcher(self):
        self.machine_watcher_thread = threading.Thread(target=self.machine_watcher)
        self.machine_watcher_thread.setDaemon(True)
        self.machine_watcher_thread.start()

    # execute rsync command.
    def exec_rsync(self):
        log.debug_ts_msg('Start: rsync execution.')
        return_val = True
        try:
            log.info('    Executing: ' + ' '.join(self.rsync_command))
            self.rsync_process = subprocess.Popen(self.rsync_command,
                                                  shell=False,
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.STDOUT,
                                                  close_fds=True,
                                                  universal_newlines=True)
            output = self.rsync_process.stdout.read()
            log.debug('    ' + output.replace('\n', '\n    '))
            log.if_in_line('warning', 'rsync: ', output)
            log.if_in_line('warning', 'rsync error: ', output)
            log.if_in_line('info', 'bytes/sec', output)
            log.if_in_line('info', 'total size is ', output)
        except (subprocess.SubprocessError, subprocess.CalledProcessError) as e:
            if e.returncode and e.returncode != 23:
                log.warning('    Error: Unknown Rsync Exit Code')
                return_val = False
        self.rsync_process = None
        log.debug_ts_msg('End: rsync execution.\n')
        return return_val

    @staticmethod
    # Determine if a snapshot is due.
    def is_due(_type, intervals, timestamp):
        if _type not in intervals:
            log.critical("    Critical: No time interval set for type: " + _type)
            exit_main()
        cycle_time = intervals[_type]
        if not isinstance(timestamp, str) or not timestamp:
            timestamp = '1970-01-01 00:00:00'
        _format = "%Y-%m-%d %H:%M:%S"
        timestamp = time.mktime(datetime.datetime.strptime(timestamp, _format).timetuple())
        time_now = int(time.time())
        if time_now - cycle_time >= timestamp:
            return True
        else:
            return False

    # Get all deprecated snapshot dirs.
    # Dirs that contain snapshots that are older than what the user wants to keep.
    # The keep range is defined in config.
    @staticmethod
    def get_deprecated_dirs(dest, snapshot, snapshots):
        deprecated = []
        base_dir = clean_path(dest + '/' + snapshot + ".")
        keep_range = range(snapshots[snapshot] - 2, -1, -1)
        active = [base_dir + str(num) for num in keep_range]
        active.append(base_dir + '0.tmp')
        deprecated.extend([_dir for _dir in glob.glob(base_dir + '*') if _dir not in active])
        return deprecated

    # Delete deprecated snapshot directories.
    def del_deprecated_snaps(self, dest, snapshot, snapshots):
        return_val = True
        deprecated = self.get_deprecated_dirs(dest, snapshot, snapshots)
        for _dir in deprecated:
            log.debug_ts_msg('  Deleting deprecated snapshot: ' + _dir)
            if check_path(_dir) == 'dir':
                try:
                    subprocess.check_output(['rm', '-rf', str(_dir)])
                except subprocess.CalledProcessError as e:
                    log.debug(e)
                    log.error('    Error: Could not delete deprecated snapshot' + _dir)
                    return_val = False
        return return_val

    # Increase the dir num by one for selected snapshot type.
    # Use the keep amount that is defined in config to find out how many dirs need to be changed.
    @staticmethod
    def shift_snaps(dest, snapshot, snapshots):
        log.debug_ts_msg('  Shifting snapshots.')
        output = True
        raw_path = clean_path(dest + '/' + snapshot + '.')
        for num in range(snapshots[snapshot] - 1, -1, -1):
            if check_path(raw_path + str(num)) == 'dir':
                try:
                    os.rename(raw_path + str(num), raw_path + str(num + 1))
                except OSError as e:
                    log.debug(e)
                    log.critical('    Critical Error: Could not rename dir: '
                                 + raw_path + str(num)) + '==> ' + str(num + 1)
                    output = False
        return output

    @staticmethod
    def update_timestamp(dest, snapshot, timestamps):
        log.debug_ts_msg('  Updating timestamp.')
        timestamps[snapshot] = time.strftime('%Y-%m-%d %H:%M:%S')
        write_yaml(timestamps, clean_path(dest + '/' + TIMESTAMP_FILE))

    @staticmethod
    def remove_incomplete_snapshots(dest):
        output = True
        if check_path(dest) == 'dir':
            log.debug_ts_msg('  Removing old incomplete snapshot: ' + dest.split('/')[-1])
            try:
                subprocess.check_output(['rm', '-rf', dest])
            except subprocess.CalledProcessError as e:
                log.debug(e)
                log.critical('    Critical Error: Could not remove : ' + dest)
                output = False
        return output

    def make_hardlinks(self, src, dest):
        log.debug_ts_msg('  Making links from: ' + src.split('/')[-1] + ' to '
                         + dest.split('/')[-1])
        return_val = True
        try:
            self.hardlink_process = subprocess.Popen(['cp', '-al', src, dest],
                                                     shell=False,
                                                     stdin=subprocess.PIPE,
                                                     stdout=subprocess.PIPE,
                                                     stderr=subprocess.STDOUT,
                                                     close_fds=True,
                                                     universal_newlines=True)
            output = self.hardlink_process.stdout.read()
            if output:
                log.debug(output)
        except (subprocess.SubprocessError, subprocess.CalledProcessError) as e:
            log.debug(e)
            log.error('    Critical Error: Could not make hardlinks for: ' + src)
            return_val = False
        self.hardlink_process = None
        return return_val

    @staticmethod
    def rename_successful_snapshot(old):
        new = old.replace('.tmp', '')
        output = True
        log.debug_ts_msg('  Renaming snapshot from: '
                         '' + old.split('/')[-1] + ' to: ' + new.split('/')[-1])
        try:
            subprocess.check_output(['mv', old, new])
        except subprocess.CalledProcessError as e:
            log.debug(e)
            log.critical('    Critical Error: Could not rename dir from: ' + old + ' to: ' + new)
            output = False
        return output

    # Create hardlinks from 'backup.latest' to each queried
    #   snapshot dir. E.g. 'hourly.0', 'weekly.0', ...
    def make_snapshots(self):
        output = True
        for snapshot in self.due_snapshots:
            log.debug_ts_msg('Start: processing snapshot: ' + snapshot)
            source = clean_path(self.dest + '/backup.latest')
            snap_dest = clean_path(self.dest + '/' + snapshot + '.0.tmp')
            if not self.remove_incomplete_snapshots(snap_dest):
                continue
            if not self.make_hardlinks(source, snap_dest):
                continue
            if not self.del_deprecated_snaps(self.dest, snapshot, self.snapshots):
                continue
            if not self.shift_snaps(self.dest, snapshot, self.snapshots):
                continue
            if not self.rename_successful_snapshot(snap_dest):
                continue
            self.update_timestamp(self.dest, snapshot, self.timestamps)
            log.debug_ts_msg('  Successfully created snapshot: ' + snapshot)
        log.debug_ts_msg('End: processing snapshots.')
        log.info('')
        return output

    def exit(self, code):
        log.job_out(code, self.init_time)
        if self.rsync_process:
            self.rsync_process.kill()
        if self.hardlink_process:
            self.hardlink_process.kill()
        self.alive = False


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
        self.logger.info(time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + new_msg)

    def debug_ts_msg(self, message=''):
        self.logger.debug('    ' + time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + message)


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
    output = None
    file_dir = os.path.dirname(file)
    if not check_path(file_dir) == 'dir':
        log.critical('    Error: Could not find dir :' + file_dir)
        exit_main()
    try:
        with open(file, 'r') as stream:
            output = yaml.safe_load(stream)
    except FileNotFoundError:
        if not create_new:
            log.critical('    Error: Could not read file :' + file)
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


def exit_main():
    log.debug('Exit Program.')
    sys.exit()


def main():
    cfg_data = load_yaml(CFG)
    app = App(cfg_data)
    # Loop through each job that is defined in the cfg.
    for _id, job_cfg in enumerate(app.jobs):
        job = Job(_id, job_cfg, app)  # Create job instance with job config data.
        job.init_time = time.time()  # set initial timestamp
        if not job.due_snapshots:
            log.job_out(1, job.init_time, 'No dues for: ' + job.src)
            continue
        if not job.is_machine_online():
            message = 'Source offline: ' + job.src_ip + ' Due: ' + ', '.join(job.due_snapshots)
            log.job_out(1, job.init_time, message)
            continue
        log.info(time.strftime('%Y-%m-%d %H:%M:%S') + ' [Executing] ' + job.src + '\n')
        log.info('    Due: ' + ', '.join(job.due_snapshots))
        if not job.check_valid_file():
            job.exit(2)
            continue
        if not job.check_dest():
            job.exit(2)
            continue
        job.start_machine_watcher()
        if not job.exec_rsync():
            job.exit(2)
            continue
        if job.alive and not job.make_snapshots():
            job.exit(2)
            continue
        job.exit(0)
    exit_main()


if __name__ == "__main__":
    log = Log('main')
    log = log.logger
    lock = check_lock(LOCK_FILE)
    try:
        main()
    except KeyboardInterrupt:
        log.error('Error: Backup aborted by user.')
        exit_main()
    except Exception as err:
        log.error('Error: An Exception was thrown.')
        log.error(str(err))
        exit_main()
