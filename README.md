# ubuntu-watch-packages
Watch specified packages in the ubuntu archive for transition between archive pockets. Useful when waiting for a package update to be published.

It polls the launchpad API for new packages every 10 minutes (you can change this by using poll-seconds option)

### Installation

```
sudo snap install ubuntu-watch-packages
```

Or

```
sudo apt install python-apt notify-send
git clone https://github.com/philroche/ubuntu-watch-packages.git
mkvirtualenv --python=/usr/bin/python3 ubuntu-watch-packages
toggleglobalsitepackages
python setup.py
python ubuntu_watch_packages.py --help
```

babel
click
pyyaml
readchar
jinja2
humanize

### System requirements (If not using the snap):

- [python-apt](https://packages.ubuntu.com/bionic/python-apt)
- [python3-launchpadlib](https://packages.ubuntu.com/bionic/python3-launchpadlib)
- [python3-distro-info](https://packages.ubuntu.com/bionic/python3-distro-info)
- [notify-send](https://packages.ubuntu.com/bionic/libnotify-bin)
- [distro_info](https://packages.ubuntu.com/bionic/distro_info)

### Python dependencies (If not using the snap):

- [readchar](https://pypi.python.org/pypi/readchar)
- [click](https://pypi.python.org/pypi/click)
- [babel](https://pypi.python.org/pypi/Babel)
- [pyyaml](https://pypi.python.org/pypi/PyYAML)
- [jinja2](https://pypi.python.org/pypi/jinja2)
- [humanize](https://pypi.python.org/pypi/humanize)

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

If you want to specify your own config yaml. When using the
ubuntu-watch-packages snap this config must reside under $HOME.

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

If you want information rendered to HTML

```
ubuntu-watch-packages --rendertohtml
```

If you want to specify where the rendered HTML should be saved

```
ubuntu-watch-packages --output-directory="~/mydirectory"
```

If you only want to poll once

```
ubuntu-watch-packages --runonce
```

Any/All of the above options can be combined.

To view a list of all options and help text

```
ubuntu-watch-packages --help
```

Once started ubuntu-watch-packages will send a desktop notification when a
new package version is discovered in the -proposed -updates or -security
Ubuntu archive pockets.


