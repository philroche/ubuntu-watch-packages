# ubuntu-watch-packages
Watch specified packages, using [rmadison](http://manpages.ubuntu.com/manpages/artful/en/man1/rmadison.1.html), in the ubuntu archive for transition between archive pockets. Useful when waiting for a package update to be published.

It polls for new packages every 5 minutes (you can change this by using poll-seconds option)

### Dependencies:

- [python-apt](https://packages.ubuntu.com/artful/python-apt)
- [click](https://packages.ubuntu.com/artful/python-click)
- [rmadison](https://packages.ubuntu.com/artful/devscripts)
- [notify-send](https://packages.ubuntu.com/artful/libnotify-bin)

## Usage

We do use time.sleep which is blocking so it is best to 'nice'
the process to reduce CPU usage.

```
nice -n 19 python ubuntu-watch-packages.py
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

OR if you want to specify your own config yaml

```
nice -n 19 python ubuntu-watch-packages.py \
--config="your-ubuntu-watch-packages-config.yaml"
```


OR if you want to specify your own polling interval

```
nice -n 19 python ubuntu-watch-packages.py \
--poll-seconds=1200
```
