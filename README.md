# ubuntu-watch-packages
Watch specified packages, using [rmadison](http://manpages.ubuntu.com/manpages/artful/en/man1/rmadison.1.html), in the ubuntu archive for transition between archive pockets. Useful when waiting for a package update to be published.

It polls for new packages every 10 minutes (you can change this by using poll-seconds option)

### Installation

```
sudo snap install --classic ubuntu-watch-packages
```

Or

```
sudo apt install python-apt rmadison notify-send
git clone https://github.com/philroche/ubuntu-watch-packages.git
mkvirtualenv --python=/usr/bin/python3 ubuntu-watch-packages-scratch
toggleglobalsitepackages
python setup.py
python ubuntu_watch_packages.py --help
```

### System requirements:

- [python-apt](https://packages.ubuntu.com/artful/python-apt)
- [rmadison](https://packages.ubuntu.com/artful/devscripts)
- [notify-send](https://packages.ubuntu.com/artful/libnotify-bin)

### Python dependencies:

- [readchar](https://pypi.python.org/pypi/readchar)
- [click](https://pypi.python.org/pypi/click)

## Snap Usage

```
ubuntu-watch-packages
```

which will watch for the following packages:

```yaml
ubuntu-versions:
  trusty:
    packages:
     - linux
     - linux-lts-xenial
  xenial:
    packages:
     - linux
  artful:
    packages:
     - linux
```

If you want to specify your own config yaml

```
ubuntu-watch-packages --config="your-ubuntu-watch-packages-config.yaml"
```


If you want to specify your own polling interval

```
ubuntu-watch-packages --poll-seconds=1200
```

If you want to specify your own polling interval

```
ubuntu-watch-packages --poll-seconds=1200
```

If you want more information displayed in console

```
ubuntu-watch-packages --logging-level=INFO
```

Any/All of the above options can be combined.

To view a list of all options and help text

```
ubuntu-watch-packages --help
```

Once started ubuntu-watch-packages will send a desktop notification when a
new package version is discovered in the -proposed -updates or -security
Ubuntu archive pockets.


