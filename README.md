# Very Hungry Pi
<img src="assets/logo_vhpi.jpg" alt="Logo" style="width: 200px;" />

## Contents
* [Description](#description)
* [Features](#features)
* [Requirements](#requirements)
* [Example Config](#example_config)
* [Installation & Configuration](#install)

## <a name="description"></a> Description
With **vhpi** you can turn your Raspberry Pi into a silent backup farm for your Network.
*Vhpi* creates [incremental](https://en.wikipedia.org/wiki/Incremental_backup) [snapshot](https://github.com/feluxe/very_hungry_pi/wiki/Snapshots-explanation) backups of available network shares (e.g. [NFS](https://en.wikipedia.org/wiki/Network_File_System), [Samba](https://en.wikipedia.org/wiki/Samba_(software))) silently and automated with a minimum of disk space required.
*Vhpi* runs entirely on 'server-side'; clients only need to share/export backup sources with the Pi and let the Pi run the backups in the background. 
*Vhpi* uses [rsync](https://en.wikipedia.org/wiki/Rsync) to create the backups and [cp](https://en.wikipedia.org/wiki/Cp_(Unix)) to create hardlinks for the snapshots. 
To get the most control over the backups *vhpi* takes raw [rsync options](https://linux.die.net/man/1/rsync) for configuration.
*Vhpi* writes two log files: one for a short overview of the entire process ([info.log exmpl.](examples/log/info.log)) and one for debugging ([debug.log exmpl.](examples/log/debug.log)).

More details about the script (if you are interested): ['What the script does in detail'](https://github.com/feluxe/very_hungry_pi/wiki/What-the-script-does-in-detail).

TL;DR: Just setup vhpi, run your Pi 24/7 and don't care about backups no more.
<br>

## <a name="features"></a> Features

* *Vhpi* works with any rsync command you like. This gives you a wide variety of configuration  options for your backup.
* You can create multiple *exclude-lists* to exclude files/dirs from the backup. (See 'exclude_lib' in [Example Config](#example_config)) 
* *Vhpi* creates [snapshots](https://github.com/feluxe/very_hungry_pi/wiki/Snapshots-explanation) for any time-interval you like. (e.g. 'hourly', 'daily', 'weekly', 'monthly', 'each-4-hours', 'half-yearly', etc...) Just add the interval name and its duration in seconds to the config. (See 'intervals' in [Example Config](#example_config)).
* You can set the amount of snapshots that you want keep for each used interval.
    E.g. if you want to keep 3 snapshots for the 'hourly' interval you get three snapshot dirs: `hourly.0`, `hourly.1`, `hourly.2`. Each snapshot reaches an hour further into the past.
* Snapshots require a minimum of disk space:
    * because the backups are created incrementally. 
    * because *vhpi* creates new snapshots as 'hard links' for all files that haven't changed. (No duplicate files.. just links)
* The process is nicely logged ('info.log', 'debug.log').
* If a backup process takes a long time, *vhpi* blocks any attempt to start a new backup process until the first one has finished to prevent the Pi from overloading. 

##<a name="requirements"></a> Requirements:

* You need Python >= 3.4 on your Pi for *vhpi* to run.
* The file system of your Backup destination has to support hard links. (most common fs like NTFS and ext do...)

## <a name="example_config"></a> Example Config 

 ```yaml  
# Basic App config:
app_cfg:
  # Add default lists for exclude files under exclude_lib.
  # You can use exclude lists for a job if you  add them under jobs_cfg -> exclude_list
  exclude_lib:
    standard_list: [
      lost+found/*,
      .cache/chromium/*,
      .mozilla/firefox/*/Cache,
      .cache/thumbnails/*,
      .local/share/Trash/*
    ]
    another_list: [
      some_dir
    ]
  # Here you can define time intervals, which you may use for your snapshots.
  # Define any interval you want e.g. 'hourly: 3600'
  # Feel free to use your own definitions like 'every_four_hours: 14400' etc.
  # Values must be in Seconds.
  intervals: {
    hourly: 3600,
    six-hourly: 21600,
    daily: 86400,
    weekly: 604800,
    monthly: 2592000,
    yearly: 31536000
  }

# Add configuration for each backup source here.
jobs_cfg:

  # Source 1:
  - source_ip: '192.168.178.20'             # The ip of the computer to which the mounted src dir belongs to. If it's a local source use: "127.0.0.1"
    rsync_src: tests/dummy_src/src1/        # The path to the mounted or local dir.
    rsync_dest: tests/dummy_dest/dest1/     # The path to the destination dir in which the snapshots are created.
    rsync_options: '-aAHSvX --delete'       # The options that you want to use for your rsync backup. Default is "-av". More info on rsync: http://linux.die.net/man/1/rsync
    exclude_lists: [                        # Add exclude lists to exclude a list of file/folders. See above: app_cfg -> exclude_lib 
      standard_list,
      another_list
    ]
    excludes: [                             # Add additional source specific exclude files/dirs that are not covered by the exclude lists.
      downloads,
      tmp
    ]
    snapshots:                              # Define how many snapshots you want to keep of each interval that you wish to use. Older snapshots are deleted automatically.
      hourly: 0
      six-hourly: 0
      daily: 7
      weekly: 4
      monthly: 6
      yearly: 6
      
  # Source 2:
  - source_ip: 192.168.178.36
   # etc.. reapt stuff from 'Source 1'
   
 ```
 
## <a name="install"></a> Installation & Configuration


### Share backup sources with the Pi:

Your Pi needs access to the directories of each client that you want to backup. Just share/export them with `NFS` or `Samba` (There are plenty tutorials online).
Perhaps you can backup local directories of your Pi as well. 

You should use `autofs` or similar to automatically mount the shared directories with your Pi when ever they are available. This way you don't have to manually share them each time your Pi or a client reboots.

### Get vhpi:

I haven't had the time to create a .deb package for an automated setup, so for now you need to setup the script manually. Just follow the steps below.


Either download the [zip from github](https://github.com/feluxe/very_hungry_pi/archive/master.zip) and unzip it to `/opt/very_hungry_pi`<br>
Or clone the repository to `/opt/very_hungry_pi`.

```
$ cd /opt
$ sudo git clone https://github.com/feluxe/very_hungry_pi.git
```
        
### Copy config files into user's home.

vhpi will look in `~/.very_hungry_pi/` for config files. Just copy them from /opt/very_hungry_pi/data/* to ~/.very_hungry_pi

```
$ mkdir ~/.very_hungry_pi
$ cp -r /opt/very_hungry_pi/example/config/* ~/.very_hungry_pi/
```

In case you want to run vhpi as root, you have to put the config in `/root/.very_hungry_pi`

### Configure vhpi:

Just have a look at the [example config](#example_config), it is self explanatory.<br>
The path to the config file must be this one: `~/.very_hungry_pi/config.yaml` (Like it was described in the step above..)


### Create validation files

Before vhpi starts a backup it validates if the source directory is readable and all good to go.
In order to do so it looks for a validation file in each source.
You must create the validation file manually.<br>
<br>
Create an empty file named '.backup_valid' in each directory that you want to backup E.g.:

```
$ touch /path/to/src1/.backup_valid
```


### Test the configuration 

If you are not already familiar with rsync, this is a little advice on how to configure a first test-run.
If you run vhpi for the first time you should use the rsync `--dry-run` flag.  That way the backup is just simulated:

```
-n, --dry-run               perform a trial run with no changes made
```

So a good command to test the config would be `-avn --delete`
`-a` = archive mode. This is the standard backup mode for rsync. 
`-v` = verbose mode. This option increases the amount of information you are given during rsync execution.
`-n` = dry-run. See above.
`--delete` = This option deletes all files that are found in the backup but not in the source. This is very important. If you don't add it your snapshots will be flooeded with deprecated files.
 
More on rsync options can be found here: http://linux.die.net/man/1/rsync
 
Now you should be ready to test-run vhpi manually like that:
 ```
 $ cd /opt/very_hungry_pi/
 $ python3 -m vhpi.main
 ```
 If you get an error use the given information to adjust the config/setup.
 You can find the results of each execution in the log files as well (.very_hungry_pi/debug.log and .very_hungry_pi/info.log)
 If the configuration works like expected you should create a cronjob to make your Pi run vhpi automatically. (see the next step.)
 

### <a name="create_cronjob"></a> Create a cronjob

For most convienice your Pi should create its backups automatically. A good way to make that happen is to create a cronjob, which executes vhpi in an interval.

To run vhpi every hour you can just add the following line to `/etc/crontab`. Replace `username` with the username that is supposed to run vhpi. (in most cases that would be `root`)
```
@hourly         username   cd /opt/very_hungry_pi/ && python3 -m vhpi.main
```

You can use any time interval you like, but keep in mind that the time interval should be at least as small as the smallest used snapshot interval. E.g. if you want to create hourly snapshots the cronjob should run vhpi at least every hour, otherwise you won't get a snapshot for each hour.
Another thing to keep in mind: The more frequently your cronjob runs vhpi the greater is the chance that it catches the source computers running. E.g. if you use a cronjob that starts evert 24 hours the chances that your source machines are offline at the moment of execution may be very high. If you are unlucky vhpi won't catch the source computer online to create a backup for many days.
So even if your smallest snapshot should happen on a daily bases, you should consider making the cronjob run vhpi each hour or so.

You can also add multiple cronjobs that execute vhpi in different intervals from different users.

After you added the cronjob, you should restart your pi or restart the crontab like this:

```
$ /etc/init.d/cron restart
```

Now vhpi should start every hour and you should see some activity in the log files and of cause on your hard drive.
