import sys
import os
from headlines import h2, h3
from buildlib.utils.yaml import load_yaml
from buildlib.cmds.build import build_python_wheel, inject_interface_txt_into_readme_md

CWD = os.getcwd()
CFG = load_yaml(CWD + '/CONFIG.yaml', keep_order=True)


def build_sequence() -> None:
    print(h2('Build'))

    result = []


    # interface_file = CWD + '/' + CFG['proj_package_name'] + '/cli/interface.txt'
    # result.append(inject_interface_txt_into_readme_md(interface_file))

    result.append(build_python_wheel(clean_dir=True))

    print(h3('Build Results'))
    for command in result:
        print(command.summary)


def execute() -> None:
    try:
        build_sequence()
    except KeyboardInterrupt:
        print('\n\nScript aborted by user. (KeyboardInterrupt)')
        sys.exit(1)


if __name__ == '__main__':
    execute()
