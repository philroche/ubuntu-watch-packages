#!/usr/bin/env python3

import json
import logging
import os
import sys
import subprocess
import time
import yaml

import apt_pkg
import click
import humanize
import readchar
import pytz

from collections import OrderedDict
from distro_info import UbuntuDistroInfo
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
from pkg_resources import resource_filename
from threading import Thread

from babel.dates import format_datetime
from launchpadlib.launchpad import Launchpad

# Log in to launchpad annonymously - we use launchpad to find
# the package publish time
launchpad = Launchpad.login_anonymously('ubuntu-watch-packages', 'production')
ubuntu = launchpad.distributions["ubuntu"]
ubuntu_archive = ubuntu.main_archive

# We do use time.sleep which is blocking so it is best to 'nice'
# the process to reduce CPU usage. https://linux.die.net/man/1/nice
os.nice(19)

apt_pkg.config.set('RootDir', os.environ.get('SNAP', ''))
apt_pkg.init_system()

# Dict to store the status of each package
PACKAGE_STATUS = {}

# Which archive pockets are checked
ARCHIVE_POCKETS = ['Release', 'Proposed', 'Security', 'Updates']

# List to store a record of all message sent to desktop
NOTIFICATIONS_SENT = []

# Var to store the last datetime that we polled the launchpad API
LAST_POLL = None

# Var to store the polling interval
POLL_SECONDS = None

NOW = pytz.utc.localize(datetime.utcnow())


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
    print(json.dumps(PACKAGE_STATUS, indent=4))


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


def get_package_stats(package, series, pocket):
    global LAST_POLL
    global NOW

    package_stats = {"full_version": None,
                     "version": None,
                     "date_published": None,
                     "published_age": None,
                     "link": None,
                     "binaries": {
                         "amd64": {
                             "version": None,
                             "link": None
                         },
                         "arm64": {
                             "version": None,
                             "link": None
                         }
                     }}
    try:
        lp_series = ubuntu.getSeries(name_or_version=series)
        lp_amd64_arch_series = lp_series.getDistroArchSeries(archtag='amd64')
        lp_arm64_arch_series = lp_series.getDistroArchSeries(archtag='arm64')
        package_published_sources = ubuntu_archive.getPublishedSources(
                exact_match=True,
                source_name=package,
                pocket=pocket,
                distro_series=lp_series)

        amd64_package_published_binaries = ubuntu_archive.getPublishedBinaries(
                exact_match=True,
                binary_name=package,
                pocket=pocket,
                distro_arch_series=lp_amd64_arch_series)

        arm64_package_published_binaries = ubuntu_archive.getPublishedBinaries(
                exact_match=True,
                binary_name=package,
                pocket=pocket,
                distro_arch_series=lp_arm64_arch_series)

        if len(amd64_package_published_binaries) > 0:
            amd64_package_published_binary = amd64_package_published_binaries[0]
            amd64_binary_package_version = amd64_package_published_binary.binary_package_version
            amd64_binary_link = amd64_package_published_binary.build_link.replace('api.', '').replace('1.0/', '')
            package_stats["binaries"]["amd64"][
                "version"] = amd64_binary_package_version
            package_stats["binaries"]["amd64"][
                "link"] = amd64_binary_link

        if len(arm64_package_published_binaries) > 0:
            arm64_package_published_binary = arm64_package_published_binaries[0]
            arm64_binary_package_version = arm64_package_published_binary.binary_package_version
            arm64_binary_link = amd64_package_published_binary.self_link
            package_stats["binaries"]["arm64"][
                "version"] = arm64_binary_package_version
            package_stats["binaries"]["arm64"][
                "link"] = arm64_binary_link

        if len(package_published_sources) > 0:
            package_published_source = package_published_sources[0]

            package_stats["link"] = package_published_source.self_link

            full_version = package_published_source.source_package_version
            version = full_version

            # We're really only concerned with the version number up
            # to the last int if it's not a ~ version
            if "~" not in full_version:
                last_version_dot = full_version.find('-')
                version = full_version[0:last_version_dot]

            package_stats["version"] = version
            package_stats["full_version"] = full_version
            date_published = format_datetime(
                    package_published_source.date_published)
            package_stats["date_published"] = date_published
            published_age = NOW - package_published_source.date_published
            if published_age < timedelta():
                # A negative timedelta means the time is in the future; this will be
                # due to inconsistent clocks across systems, so assume that there is no
                # delta
                published_age = timedelta()
            published_age = humanize.naturaltime(published_age)

            package_stats["published_age"] = published_age

        LAST_POLL = format_datetime(datetime.utcnow())
    except Exception as e:
        logging.error("Error querying launchpad API: %s. \n "
                      "We will retry. \n", str(e))

    return package_stats


def watch_packages(initial=False, notify_on_startup=False):
    for ubuntu_version, packages in PACKAGE_STATUS.items():
        for package in packages.keys():
            for pocket in ARCHIVE_POCKETS:
                logging.info("Getting stats for {} {} {}".format(
                        ubuntu_version, pocket.lower(), package))
                package_stats = get_package_stats(package,
                                                  ubuntu_version,
                                                  pocket)

                package_version = package_stats["version"]
                current_package_version = \
                    PACKAGE_STATUS[ubuntu_version][package][pocket]["version"]

                message = None
                newer_package = False
                new_package = False

                if package_version:
                    message = "{} {} for {} is in {} pocket (published @ {})" \
                        .format(package, package_version,
                                ubuntu_version, pocket.lower(),
                                package_stats["date_published"])

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
                            package_version, pocket.lower())
                    message = '** NEW TO POCKET ** {}. {}'.format(
                        message, is_new_message)

                # If the package is newer or it's a new package send
                # a notification
                if newer_package or initial or new_package:
                    PACKAGE_STATUS[ubuntu_version][package][pocket] \
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
    tmpl = env.get_template('package-stats.html')

    # sort the package stats
    correct_order = [rel.series for rel in UbuntuDistroInfo()._releases]

    package_stats = OrderedDict(sorted(package_stats.items(),
                                       key=lambda i:correct_order.index(i[0])))

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
                   'generation_time': NOW}
        out_file.write(tmpl.render(context))
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
@click.pass_context
def ubuntu_watch_packages(ctx, config, poll_seconds, logging_level,
                          config_skeleton, notify_on_startup, runonce,
                          rendertohtml, output_directory):
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

    # Set global POLL_SECONDS as this is used in the status dump
    POLL_SECONDS = poll_seconds

    # We log to stderr so that a shell calling this will not have logging
    # output in the $() capture.
    level = logging.getLevelName(logging_level)
    logging.basicConfig(level=level, stream=sys.stderr,
                        format='%(asctime)s [%(levelname)s] %(message)s')

    default_package_stats = {"full_version": None,
                             "version": None,
                             "date_published": None,
                             "published_age": None,
                             "link": None,
                             "binaries": {
                                 "amd64": {
                                     "version": None,
                                     "link": None
                                 },
                                 "arm64": {
                                     "version": None,
                                     "link": None
                                 }
                             }}
    default_package_versions = {'Release': default_package_stats,
                                'Proposed': default_package_stats,
                                'Updates': default_package_stats,
                                'Security': default_package_stats}

    # Parse config
    with open(config, 'r') as config_file:
        package_config = yaml.load(config_file)
        if config_skeleton:
            output = yaml.dump(package_config, Dumper=yaml.Dumper)
            print("# Sample config.")
            print(output)
            exit(0)

    ubuntu_versions = package_config.get('ubuntu-versions', {})

    # initialise package status
    for ubuntu_version, packages in ubuntu_versions.items():
        package_list = packages.get("packages", [])
        PACKAGE_STATUS.setdefault(ubuntu_version,
                                  {package: default_package_versions.copy()
                                   for package in package_list})
    # Initialise all package version
    watch_packages(initial=True,
                   notify_on_startup=notify_on_startup)
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
            watch_packages()
            if rendertohtml:
                render(PACKAGE_STATUS, output_directory, package_config)
    else:
        print_stats()


if __name__ == '__main__':
    cli(obj={})
