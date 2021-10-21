### Future

-   [ ] Add build script that builds vhpi via 'pyinstaller' or 'nuitka'.
-   [ ] Create webserver/interface to show log files and basic health status.
-   [ ] Dupe Replacement feature. (See issues #5)
-   [ ] Add feature to load exclude-lists from files. Use build in rsync functionality for that. (See issues #4)

### v3.0

-   [x] Allow remote backup sources (e.g. `user@192.168.178.1:/home/user`) via ssh.
-   [x] Run vhpi in a 'long running process'.
-   [x] Fix bug with some options in `rsync_options: "..."` not parsing correctly.
-   [x] Cleanup code base.

### v2.0

-   [x] Complete rewrite of the code in a more _functional_ style (no global state, more purity)
-   [x] Add Type annotations via _typing_ module.
-   [x] Updated to Python3.6
-   [x] Publish vhpi on PyPi. (package name: vhpi)
-   [x] Add Creation Timestamp to each Snapshot directory.
-   [x] Beautify log output.
-   [x] Improve logging for subprocess output (more performant and less buggy).
-   [x] Change config dir to `~/.config/vhpi/`.
-   [x] Remove log cfg file.
-   [x] Generate default config file (`~/config/vhpi/vhpi_cfg.yaml`) on startup.
-   [x] Provide a simple command line interface to run vhpi. (see `vhpi --help`)
-   [x] Fix a bunch of bugs.
-   [x] Improve test strategy.
-   [x] Add Tutorial on how to install Python3.x from source. (see wiki)
-   [x] Add Tutorial on how to share sources with the pi via NFS. (see wiki)
-   [x] Use AGPL (license).
-   [x] Add make.py build scripts.

### v1.0

Initial release.
Version history starts here...
