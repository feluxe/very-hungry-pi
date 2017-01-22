
import time
import threading
import subprocess

from .logger import log
import vhpi.settings as s


def check_validation_file(path):
    import vhpi.lib as lib
    if not lib.check_path(path) == 'file':
        return False
    return True


# check if machine is online.
def is_machine_online(ip):
    ping_command = ["ping", "-c", "1", ip]
    try:
        subprocess.check_output(ping_command)
        return True
    except subprocess.CalledProcessError:
        return False


def check_dest(dest):
    import vhpi.lib
    if not vhpi.lib.check_path(dest) == 'dir':
        return False
    return True


def check_routine(validation_file, ip, dst):
    if not check_validation_file(validation_file):
        log.critical('    Critical: Could not validate source via '
                     '"validation file"' + validation_file)
        job.exit(2)
    if not check_dest(dst):
        log.critical('    Critical: Invalid Destination:' + dst + ': '
                     + time.strftime(log.timestamp_format))
        job.exit(2)
    if not is_machine_online(ip):
        log.info('    Error: Source went offline: ' + time.strftime(log.timestamp_format))
        job.exit(2)


# Check if source is online repeatedly. If it goes offline exit program.
def monitor(validation_file, ip, dst):
    import vhpi.job as job
    while job.alive:
        check_routine(validation_file, ip, dst)
        time.sleep(60)


# Start a watcher in a thread which checks if source machine is online, etc, each 60s.
def run(validation_file, ip, dst):
    check_routine(validation_file, ip, dst)  # Initial Check before health monitor starts as thread.
    health_monitor_thread = threading.Thread(target=monitor(validation_file, ip, dst))
    health_monitor_thread.setDaemon(True)
    health_monitor_thread.start()

