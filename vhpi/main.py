# !/usr/bin/env python3
# -*- coding: utf-8 -*-

'''vhpi
Usage:
    vhpi run              [-c <config>] [-j <job> |-s <src>]...
    vhpi backup           [-c <config>] [-j <job> |-s <src>]...
    vhpi snapshot         [-c <config>] [-j <job> |-s <src>]... (<interval>)...
    vhpi timestamp update [-c <config>] (-j <job> |-s <src>)... (<interval>)...
    vhpi show  [-c <config>] [-t] [-j <job> |-s <src>]
    vhpi -h | --help
    vhpi --version

The 'run' command is like running 'backup', 'snapshot', 'timestamp update' combined.
If no --config/-c is defined, the default config file is used.
You may define one config and multiple job/src.
Each <job> and <src> must be inside the given config.

Options:
    -c <config>, --config <config>    Define a config for which to run the command.
                                      [default: ~/.very_hungry_pi/config.yaml]
    -j <job>, --job <job>             Define a job for which to run the command.
    -s <src>, --src <src>             Define a src dir (must exist in config) for which to run the
                                      command.
    -t
    -h --help                         Show this screen.
    --version                         Show version.
    --speed=<kn>                      Speed in knots [default: 10].
    --moored                          Moored (anchored) mine.
    --drifting                        Drifting mine.
'''

from __future__ import unicode_literals, print_function
import os
from docopt import docopt
from .utils import load_yaml
from . import cli

version = "1.1.0"
__version__ = version
__author__ = "Felix Meyer-Wolters"
__license__ = "GPL-3.0"

user_input = docopt(__doc__, version=__version__)
print(user_input)
print('\n\n')
home_dir = os.path.expanduser('~')
config = load_yaml(user_input['--config'].replace('~', home_dir))

exec = cli.main(user_input, config, home_dir)
