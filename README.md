# ubuntu-watch-packages
Watch specified binary packages in the ubuntu archive for transition between archive pockets. 
Useful when waiting for a package update to be published.

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
humanize
jinja2
pyyaml
readchar


### System requirements (If not using the snap):

- [notify-send](https://packages.ubuntu.com/bionic/libnotify-bin)

### Python dependencies (If not using the snap):


- [babel](https://pypi.python.org/pypi/Babel)
- [click](https://pypi.python.org/pypi/click)
- [pyyaml](https://pypi.python.org/pypi/PyYAML)
- [python-debian](https://pypi.python.org/pypi/python-debian) 
- [jinja2](https://pypi.python.org/pypi/jinja2)
- [readchar](https://pypi.python.org/pypi/readchar)
- [ubuntu-package-status](https://pypi.python.org/pypi/ubuntu-package-status)

## Snap Usage

```
ubuntu-watch-packages
```

which will watch for the following packages:

```yaml
ubuntu-versions:
  trusty:
    packages:
     - linux-generic
     - linux-lts-xenial
  xenial:
    packages:
     - linux-generic
  artful:
    packages:
     - linux-generic
```

If you want to specify your own config yaml. When using the
ubuntu-watch-packages snap this config must reside under $HOME.

```
ubuntu-watch-packages --config="your-ubuntu-watch-packages-config.yaml"
```

If you want to specify a specific architecture to query

```
ubuntu-watch-packages --package-architecture=amd64
```

If you want to specify multiple architectures to query

```
ubuntu-watch-packages --package-architecture=amd64 --package-architecture=arm64
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


