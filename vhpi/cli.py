import itertools
from vhpi.logging import logger as log
from vhpi import snapshot

# This module takes the CLI input. validates it, remodels it and calls the submodules.

def new_backup():
    pass


def new_snapshot(user_input, cfg):
    #
    # if no job / src
    #   all jobs from cfg
    # else:
    #   check if job/src inside config.

    targets = user_input['--src']
    targets += [job['rsync_dst'] for job in cfg['jobs'] if job['name'] in user_input['--job']]
    targets = [target + '/backup.latest' for target in targets]
    intervals = user_input['<interval>']
    args = itertools.product(intervals, targets)
    try:
        [snapshot.make(interval, source) for interval, source in args]
    except FileNotFoundError as e:
        log.debug('    ' + str(e))
        log.error('    Error: [File not found] Could not create snapshot.')


def main(user_input, cfg, home_dir):

    if user_input['run']:
        pass

    if user_input['backup']:
        pass

    if user_input['snapshot']:
        new_snapshot(user_input, cfg)


