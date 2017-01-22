import os
import pytest
import shutil
import glob
from vhpi import snapshot

cwd = os.getcwd()
dummies = cwd + '/tests/dummy_files'



def test_remove_success():
    """This creates a dir and removes it with snapshot.remove()."""
    snap_dir_parent = dummies + '/removing_snapshots'
    snap_dir = snap_dir_parent + '/snap_dir_del'
    if not os.path.exists(snap_dir):
        os.makedirs(snap_dir)
        if not os.path.isdir(snap_dir):
            raise NotADirectoryError

    # Check if dir was there before.
    before_is_dir = os.path.isdir(snap_dir)
    assert before_is_dir is True

    # Check if dir was removed.
    snapshot.remove(snap_dir)
    after_is_dir = os.path.isdir(snap_dir)
    assert after_is_dir is False


def test_create_hardlinks():
    """This tries to make hard links from the dummy source."""
    src = dummies + '/making_hardlinks/hardlink_src'
    dst = dummies + '/making_hardlinks/hardlink_dst'

    # Cleanup: Remove dst
    shutil.rmtree(dst) if os.path.exists(dst) else None

    # Check if snapshot src is correct
    before_src_len = len(os.listdir(src))
    assert before_src_len == 4

    # Check if snapshot destination does not exist.
    before_dst_is_dir = os.path.isdir(dst)
    assert before_dst_is_dir is False

    # Check if create_hardlinks() creates dst dir.
    snapshot.create_hardlinks(src, dst)
    assert os.path.isdir(dst) is True

    # Check if src == dst
    after_dst_len = len(os.listdir(dst))
    assert after_dst_len is 4

    # TODO: Du warst gerade dabei zu debuggen, warum diesr test fehlschlägt.
    # TODO:  Aus irgendeinem grund werden die Hardlinks im Falschen Ordner erstellt.
    # TODO: Schaue dir diesen Ordner: tests/dummy_files/making_hardlinks/hardlinl_dst an
    # TODO:  und zwar einmal ohne diesen letzten test und einmal mit.
    # TODO: Teste mal vhpi.snapshot create_hardlinks() manuell im interpreter.
    # Check if create_hardlinks() complains if dst already exists.
    with pytest.raises(FileExistsError):
        snapshot.create_hardlinks(src, dst)


def test_shift():
    parent_dir = dummies + '/shifting_snapshots'
    snap_base = parent_dir + '/hourly.'

    # Set up dummy snapshots and shift
    shutil.rmtree(parent_dir) if os.path.exists(parent_dir) else None
    os.makedirs(parent_dir)
    for i in range(0, 5):
        os.makedirs(snap_base + str(i))
    snapshot.shift('hourly', parent_dir)

    # Check if .0 not exist
    # Check if .1 is dir.
    # Check if .5 is dir
    # Check if .6 not exist
    assert os.path.exists(snap_base + '0') == False
    assert os.path.isdir(snap_base + '1') == True
    assert os.path.isdir(snap_base + '5') == True
    assert os.path.isdir(snap_base + '6') == False


def test_make():
    parent = dummies + '/making_snapshots'
    src = parent + '/backup.latest'
    for _snapshot in glob.glob(parent + '/hourly.*'):
        shutil.rmtree(_snapshot)
    snapshot.make('hourly', src)
    snapshot.make('hourly', src)
    snapshot.make('hourly', src)

