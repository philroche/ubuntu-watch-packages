# ubuntu-watch-packages
Watch specified packages in the ubuntu archive for transition between  
archive pockets. Useful when waiting for a package update to be published

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
