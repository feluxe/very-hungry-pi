import os
import shutil
import subprocess as sp

from buildlib import buildmisc, git, project, wheel, yaml_
from cmdi import print_summary
from docopt import docopt

interface = """
Install:
    pipenv install --dev --pre
    pipenv run python make.py

Usage:
    make.py build [options]
    make.py deploy [options]
    make.py test <cmd> [options]
    make.py bump [options]
    make.py git [options]
    make.py -h | --help

Commands:
    test <cmd>           <cmd> can be 'init' or 'run'. 'init' creates a test
                            directory and 'run' runs the tests.

Options:
-h, --help               Show this screen.
"""

proj = yaml_.loadfile("Project")


class Cfg:
    version = proj["version"]
    registry = "pypi"


def build():
    return wheel.cmd.build(clean_dir=True)


def deploy(cfg: Cfg):
    return wheel.cmd.push(clean_dir=True, repository=cfg.registry)


def test(cfg: Cfg, cmd: str):

    if cmd == "init":
        shutil.rmtree("/tmp/vhpi/", ignore_errors=True)
        os.makedirs("/tmp/vhpi/")
        shutil.copytree(src="tests", dst="/tmp/vhpi/tests")
        print("Created test directory at: /tmp/vhpi/tests")

    elif cmd == "run":
        sp.run(['python', '-m', 'vhpi.app', 'run', '--config-dir', '/tmp/vhpi/tests'])


def bump(cfg: Cfg):

    results = []

    if project.prompt.should_bump_version():
        result = project.cmd.bump_version()
        cfg.version = result.val
        results.append(result)

    if wheel.prompt.should_push("PYPI"):
        results.append(deploy(cfg))

    new_release = cfg.version != proj["version"]

    results.extend(git.seq.bump_git(cfg.version, new_release))

    return results


def run():

    cfg = Cfg()
    uinput = docopt(interface)
    results = []

    if uinput["build"]:
        results.append(build(cfg))

    if uinput["deploy"]:
        results.append(deploy(cfg))

    if uinput["test"]:
        test(cfg, uinput["<cmd>"])

    if uinput["git"]:
        results.append(git.seq.bump_git(cfg.version, new_release=False))

    if uinput["bump"]:
        results.extend(bump(cfg))

    print_summary(results)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nScript aborted by user.")
