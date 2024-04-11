#!/usr/bin/env python3

import json
import logging
import os
import sys
import subprocess
import time
import yaml

import click
import readchar
import pytz

from babel.dates import format_datetime
from collections import OrderedDict
from debian import debian_support
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from pkg_resources import resource_filename
from threading import Thread
from ubuntu_package_status import ubuntu_package_status


# We do use time.sleep which is blocking so it is best to 'nice'
# the process to reduce CPU usage. https://linux.die.net/man/1/nice
os.nice(19)

# Dict to store the status of each package
PACKAGE_STATUS = {}

# List to store a record of all message sent to desktop
NOTIFICATIONS_SENT = []

# Var to store the last datetime that we polled the launchpad API
LAST_POLL = None

# Var to store the polling interval
POLL_SECONDS = None

NOW = pytz.utc.localize(datetime.utcnow())

SUMMARY_ONLY = False  # If True only print the summary


def keypress():
    interrupt_print = readchar.readchar()
    if interrupt_print is not None and interrupt_print == 'p':
        print("<Current Package Status pollinterval=\"{}\" "
              "lastpoll=\"{}\">".format(POLL_SECONDS, LAST_POLL))
        print_stats()
        print("</Current Package Status pollinterval=\"{}\" "
              "lastpoll=\"{}\">".format(POLL_SECONDS, LAST_POLL))
        keypress()


def print_stats():
    if not SUMMARY_ONLY:
        print(json.dumps(PACKAGE_STATUS, indent=4))
    else:
        print_stats_summary()


def print_stats_summary():
    for ubuntu_version, package_stats in PACKAGE_STATUS.items():
        print(ubuntu_version)
        for package, pockets in package_stats.items():
            print("\t{}".format(package))
            for pocket, architectures in pockets.items():
                print("\t\t{}".format(pocket))
                for architecture, stats in architectures.items():
                    if stats['full_version']:
                        print("\t\t\t{} {} @ {} ({})".format(
                                architecture,
                                stats['full_version'],
                                stats['date_published_formatted'],
                                stats['published_age'],
                        ))


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


def watch_packages(package_config, initial=False, notify_on_startup=False, package_architectures=["amd64"]):
    global PACKAGE_STATUS
    global LAST_POLL

    updated_package_status = ubuntu_package_status.get_status_for_all_packages(package_config, package_architectures)
    LAST_POLL = format_datetime(datetime.utcnow())

    # This is the first time we have polled/watched these packages so set the global variable PACKAGE_STATUS
    # to the current polled stats
    if initial:
        PACKAGE_STATUS = updated_package_status

    for ubuntu_version, packages in PACKAGE_STATUS.items():
        for package, pockets in packages.items():
            for pocket, architectures in pockets.items():
                for architecture, package_stats in architectures.items():
                    logging.info("Getting stats for {} {} {} {}".format(
                            ubuntu_version, pocket.lower(), architecture, package))

                    current_package_stats = updated_package_status[ubuntu_version][package][pocket][architecture]

                    current_package_version = current_package_stats["version"]

                    previous_package_version = package_stats.get("version", None)

                    message = None
                    newer_package = False
                    new_package = False

                    if current_package_version:
                        message = "{} {} {} for {} is in {} pocket (published @ {} - {})" \
                            .format(package, architecture, current_package_version,
                                    ubuntu_version, pocket.lower(),
                                    current_package_stats["date_published_formatted"],
                                    current_package_stats["published_age"])

                    # Is the version in archive greater than
                    # that in our database?
                    if current_package_version and previous_package_version:

                        vc = debian_support.version_compare(current_package_version,
                                                            previous_package_version)
                        logging.info(message)
                        if vc > 0:
                            """
                            > 0 The version current_package_version is greater than version previous_package_version.
                            
                            = 0 Both versions are equal.
                            
                            < 0 The version current_package_version is less than version previous_package_version.
                            """
                            newer_package = True
                            is_newer_message = "{} is newer than {}".format(
                                    current_package_version, previous_package_version)
                            message = '** NEW VERSION ** {}. {}'.format(
                                    message, is_newer_message)

                    # Is the version in archive the first time we've seen a
                    # version in this pocket?
                    if not previous_package_version and current_package_version:
                        new_package = True
                        is_new_message = "{} is new to the {} pocket".format(
                                current_package_version, pocket.lower())
                        message = '** NEW TO POCKET ** {}. {}'.format(
                            message, is_new_message)

                    # If the package is newer or it's a new package send
                    # a notification
                    if initial or newer_package or new_package:
                        PACKAGE_STATUS[ubuntu_version][package][pocket][architecture] \
                            = package_stats
                        if message and message not in NOTIFICATIONS_SENT:
                            NOTIFICATIONS_SENT.append(message)
                            if not initial or (
                                    initial
                                    and pocket == "Proposed"
                                    and notify_on_startup):
                                send_notification_message(message)

                    if message:
                        logging.info(message)


def render(package_stats, output_directory, package_config):
    '''Render the repositories into an html file.'''
    abs_templates_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(abs_templates_path))
    package_stats_template = env.get_template('package-stats.html')

    # Make sure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    output_html_filepath = os.path.join(output_directory, 'package-stats.html')
    output_config_filepath = os.path.join(output_directory, 'config.yaml')
    output_json_filepath = os.path.join(output_directory, 'package-stats.json')
    with open(output_config_filepath, 'w') as config_outfile:
        yaml.dump(package_config, config_outfile, default_flow_style=False)

    with open(output_json_filepath, 'w') as config_outfile:
        json.dump(package_stats, config_outfile, indent=4)

    with open(output_html_filepath, 'w') as out_file:
        context = {'suites': package_stats,
                   'first_suite': list(package_stats)[0],
                   'generation_time': NOW,
                   'pockets': ubuntu_package_status.ARCHIVE_POCKETS}
        out_file.write(package_stats_template.render(context))
        print("**** {} written ****".format(output_html_filepath))
        print("file://{}".format(output_html_filepath))


@click.group()
@click.pass_context
def cli(ctx):
    pass


@cli.command()
@click.option('--config', required=False, default=resource_filename(
        'ubuntu_watch_packages', 'dist-config.yaml'),
        help="Config yaml specifying which packages ubuntu versions to watch."
             "{}".format(" When using the ubuntu-watch-packages snap this"
                         " config must reside under $HOME."
                                      if os.environ.get('SNAP', None) else ""))
@click.option('--poll-seconds', type=int, required=False, default=600,
              help="Interval, in seconds, between each version check")
@click.option('--logging-level', type=click.Choice(['DEBUG', 'INFO',
                                                    'WARNING', 'ERROR']),
              required=False, default="ERROR",
              help='How detailed would you like the output.')
@click.option('--config-skeleton', is_flag=True, default=False,
              help='Print example config.')
@click.option('--notify-on-startup', is_flag=True, default=False,
              help='Do not notify me of package version on startup. Only do '
                   'so when new package versions appear.')
@click.option('--runonce', is_flag=True, default=False,
              help='Only run this once, do not poll.')
@click.option('--summary-only', is_flag=True, default=False,
              help='Only print the summary - not all the full json dict.')
@click.option('--rendertohtml', is_flag=True, default=False,
              help='Do you want to render the stats to HTML?.')
@click.option('--output-directory', envvar='UBUNTU_WATCH_PACKAGES_OUTPUT_DIRECTORY',
              required=False, type=click.Path(), default=lambda:
              os.environ.get('SNAP_USER_COMMON', "/tmp/ubuntu_watch_packages/"),
              help="Output directory. [default: {}]. You can also set "
                   "UBUNTU_WATCH_PACKAGES_OUTPUT_DIRECTORY as an environment "
                   "variable.{}"
                   .format(os.environ.get('SNAP_USER_COMMON',
                                          "/tmp/ubuntu_watch_packages/"),
                           " When using the ubuntu_watch_packages snap this config "
                           "must reside under $HOME."
                           if os.environ.get('SNAP', None) else ""))
@click.option('--package-architecture', "package_architectures",
              help='The architecture to use when querying package '
              'version in the archive. We use this in our Launchpad '
              'query to query either "source" package or "amd64" package '
              'version. Using "amd64" will query the version of the '
              'binary package. "source" is a valid value for '
              'architecture with Launchpad and will query the version of '
              'the source package. The default is amd64.'
              'This option can be specified multiple times.',
              multiple=True,
              default=["amd64"]
)
@click.pass_context
def ubuntu_watch_packages(ctx, config, poll_seconds, logging_level,
                          config_skeleton, notify_on_startup, runonce,
                          summary_only, rendertohtml, output_directory, package_architectures):
    # type: (Text, int, Text, bool, bool) -> None
    """
    Watch specified packages in the ubuntu archive for transition between
    archive pockets. Useful when waiting for a package update to be published.

    Usage:
    python ubuntu_watch_packages.py \
    --config="your-ubuntu-watch-packages-config.yaml"
    """
    global POLL_SECONDS
    global PACKAGE_STATUS
    global NOW
    global SUMMARY_ONLY

    # Set global SUMMARY_ONLY as this is used in the print_stats
    SUMMARY_ONLY = summary_only
    # Set global POLL_SECONDS as this is used in the status dump
    POLL_SECONDS = poll_seconds

    # We log to stderr so that a shell calling this will not have logging
    # output in the $() capture.
    level = logging.getLevelName(logging_level)
    logging.basicConfig(level=level, stream=sys.stderr,
                        format='%(asctime)s [%(levelname)s] %(message)s')

    # Parse config
    with open(config, 'r') as config_file:
        package_config = yaml.safe_load(config_file)
        if config_skeleton:
            output = yaml.dump(package_config, Dumper=yaml.Dumper)
            print("# Sample config.")
            print(output)
            exit(0)

    PACKAGE_STATUS = ubuntu_package_status.initialize_package_stats_dict(package_config, package_architectures)

    # Initialise all package version
    watch_packages(package_config,
                   initial=True,
                   notify_on_startup=notify_on_startup,
                   package_architectures=package_architectures)
    if rendertohtml:
        render(PACKAGE_STATUS, output_directory, package_config)
    if not runonce:
        # Start a separate thread to wait for 'p' keypress.
        # This will print current package status
        print("Press \"p\" to see package status.")
        t = Thread(target=keypress)
        t.start()
        while True:
            time.sleep(poll_seconds)  # wait before checking again
            NOW = pytz.utc.localize(datetime.utcnow())
            watch_packages(package_config,
                           initial=True,
                           notify_on_startup=False,
                           package_architectures=package_architectures)
            if rendertohtml:
                render(PACKAGE_STATUS, output_directory, package_config)
    else:
        print_stats()


if __name__ == '__main__':
    cli(obj={})
