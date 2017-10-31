from headlines import h3
from buildlib.utils.yaml import load_yaml
from buildlib.cmds import semver
from buildlib.cmds import git
from buildlib.cmds import build
from buildlib.utils.wheel import find_python_wheel


def publish() -> None:
    """"""

    results = []
    cfg_file = 'CONFIG.yaml'

    cur_version: str = load_yaml(
        file=cfg_file,
        keep_order=True
    ).get('version')

    should_update_version: bool = build.prompt.should_update_version(
        default='y'
    )

    if should_update_version:
        version: str = semver.prompt.semver_num_by_choice(
            cur_version=cur_version
        )

    else:
        version: str = cur_version

    should_run_build_file: bool = build.prompt.should_run_build_file(
        default='y'
    )

    if should_update_version:
        results.append(
            build.update_version_num_in_cfg_yaml(
                config_file=cfg_file,
                semver_num=version
            )
        )

    if should_run_build_file:
        results.append(
            build.run_build_file(
                build_file='scripts/build.py'
            )
        )

    run_any_git: bool = git.prompt.should_run_any('y') \
                        and git.prompt.confirm_status('y') \
                        and git.prompt.confirm_diff('y')

    if run_any_git:
        should_add_all: bool = git.prompt.should_add_all(
            default='y'
        )

        should_commit: bool = git.prompt.should_commit(
            default='y'
        )

        if should_commit:
            commit_msg: str = git.prompt.commit_msg()

        should_tag: bool = git.prompt.should_tag(
            default='y' if should_update_version else 'n'
        )

        should_push_git: bool = git.prompt.should_push(
            default='y'
        )

        if any([
            should_tag,
            should_push_git
        ]):
            branch: str = git.prompt.branch()

    should_push_pypi: bool = build.prompt.should_push_pypi(
        default='y' if should_update_version else 'n'
    )

    if run_any_git:
        if should_add_all:
            results.append(
                git.add_all()
            )

        if should_commit:
            results.append(
                git.commit(commit_msg)
            )

        if should_tag:
            results.append(
                git.tag(version, branch)
            )

        if should_push_git:
            results.append(
                git.push(branch)
            )

    if should_push_pypi:
        results.append(
            build.push_python_wheel_to_pypi()
        )

    print(h3('Publish Results'))

    for i, result in enumerate(results):
        print(result.summary)


if __name__ == '__main__':
    publish()
