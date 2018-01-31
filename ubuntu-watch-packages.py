#!/usr/bin/env python3
# Displays a notification if a required package appears in the
# archive (proposed and security pockets).
import logging
import os
import sys
import subprocess
import time
import yaml

import apt_pkg
import click


apt_pkg.init_system()

# Dict to store the status of each package
PACKAGE_STATUS = {}

# Which archive pockets are checked
ARCHIVE_POCKETS = ['proposed', 'security', 'updates']

# List to store a record of all message sent to desktop
NOTIFICATIONS_SENT = []


def do_rmadison_search(pocket, package):
    """
    Runs the search for the packages using rmadison.
    """
    try:
        cmd = ['rmadison']
        cmd.extend(['-a', 'source'])
        cmd.extend(['-s', pocket])
        cmd.extend([package])
        output = subprocess.check_output(cmd)
        version = None
        if output:
            version = output.split(b"|")[1].decode('utf-8').strip()
            # We're really only concerned with the version number up
            # to the last int if it's not a ~ version
            if "~" not in version:
                last_version_dot = version.rfind('.')
                version = version[0:last_version_dot]
        return version
    except Exception as e:
        logging.error("Error querying rmadison: %s", str(e))


def send_notification_message(message):
    """
    Sends message to desktop using notify-send.
    """
    try:
        cmd = ['notify-send']
        cmd.extend(['--expire-time', '28800000'])
        cmd.extend(['--urgency', 'critical'])
        cmd.extend([message])
        subprocess.check_output(cmd)
    except Exception as e:
        logging.error("Error sending notify-send: %s", str(e))


def watch_packages(initial=False):
    for ubuntu_version, packages in PACKAGE_STATUS.items():
        for package in packages.keys():
            for pocket in ARCHIVE_POCKETS:
                logging.info("{} {} {}".format(
                        ubuntu_version, pocket, package))
                package_version = do_rmadison_search(
                        '{}-{}'.format(ubuntu_version, pocket), package)
                current_package_version = \
                    PACKAGE_STATUS[ubuntu_version][package][pocket]

                message = None
                newer_package = False
                new_package = False

                if package_version:
                    message = "{} {} for {} is in {} pocket" \
                        .format(package, package_version,
                                ubuntu_version, pocket)

                # Is the version in archive greater than
                # that in our database?
                if current_package_version and package_version:

                    vc = apt_pkg.version_compare(package_version,
                                                 current_package_version)
                    logging.info(message)
                    if vc > 0:
                        newer_package = True
                        is_newer_message = "{} is newer than {}".format(
                                package_version, current_package_version)
                        message = '** NEW VERSION ** {}. {}'.format(
                                message, is_newer_message)

                # Is the version in archive the first time we've seen a
                # version in this pocket?
                if not current_package_version and package_version \
                        and not initial:
                    new_package = True
                    is_new_message = "{} is new to the {} pocket".format(
                            package_version, pocket)
                    message = '** NEW TO POCKET ** {}. {}'.format(
                        message, is_new_message)

                # If the package is newer or it's a new package send
                # a notification
                if newer_package or initial or new_package:
                    PACKAGE_STATUS[ubuntu_version][package][pocket] = \
                        package_version
                    if message and message not in NOTIFICATIONS_SENT:
                        NOTIFICATIONS_SENT.append(message)
                        if not initial or (initial and pocket == "proposed"):
                            send_notification_message(message)

                if message:
                    logging.info(message)


@click.command()
@click.option('--config', required=False, default=os.path.join(
        os.path.dirname(__file__),
        "dist-config.yaml"),
        help="Config yaml specifying which packages ubuntu versions to watch")
@click.pass_context
def cli(ctx, config):
    # type: (Text, Text) -> None
    """
    Watch specified packages in the ubuntu archive for transition between
    archive pockets. Useful when waiting for a package update to be published.

    Usage:
    nice -n 19 python ubuntu-watch-packages.py \
    --config="your-ubuntu-watch-packages-config.yaml"
    """
    default_package_versions = {'proposed': None,
                                'updates': None,
                                'security': None}
    # Parse awslib config
    with open(config, 'r') as config_file:
        package_config = yaml.load(config_file)

    ubuntu_versions = package_config.get('ubuntu-versions', {})

    # initialise package status
    for ubuntu_version, packages in ubuntu_versions.items():
        package_list = packages.get("packages", [])
        PACKAGE_STATUS.setdefault(ubuntu_version,
                                  {package: default_package_versions.copy()
                                   for package in package_list})
    # Initialise all package version
    watch_packages(initial=True)
    while True:
        time.sleep(150)  # wait 2.5 minutes before checking again
        watch_packages()


if __name__ == '__main__':
    # We log to stderr so that a shell calling this will not have logging
    # output in the $() capture.
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr,
                        format='%(asctime)s [%(levelname)s] %(message)s')

    cli(obj={})
