#!/usr/bin/env python3

import os
import sys
import logging
import argparse
import subprocess
import git

logging.basicConfig(
    format='%(message)s',
    level=os.getenv('LOG_LEVEL', logging.INFO),
)

PACKAGE = subprocess.run(
    [sys.executable, 'setup.py', '--name'],
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
MODULE = __import__(PACKAGE)
CVERS = MODULE.__version__
VFILE = os.path.join(PACKAGE, '__version__.py')


def vers_from_str(s):
    """Return version info from version string

    Version is assumed to be "semantic" [https://semver.org/] of the
    form:

       major.minor.rev+build

    where major, minor, rev will all be ints, and build will be a str.
    Returns tuple of all components.

    """
    # check if there's a build suffix on the string
    build = ''
    vsplit = s.split('+')
    if len(vsplit) > 1:
        build = '+'+vsplit[1]
    try:
        major, minor, rev = vsplit[0].split('.')
    except ValueError:
        raise ValueError("Could not parse version string: {}".format(s))
    return int(major), int(minor), int(rev), build


def write_vfile(vers):
    with open(VFILE, 'w') as f:
        f.write("__version__ = '{}'\n".format(vers))


parser = argparse.ArgumentParser(
    description="""Make new release of python package.

package: {}
version: {}
  vfile: {}

Determines new version based on release type (major.minor.rev),
updates vfile, commits to git repo and tags, creates sdist and wheel
packages, then creates second commit to update to dev version.
""".format(PACKAGE, CVERS, VFILE),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
cgroup = parser.add_mutually_exclusive_group(required=True)
cgroup.add_argument(
    'release',
    choices=['major', 'minor', 'rev'],
    nargs='?',
    help="release type",
)
cgroup.add_argument(
    '-s', '--set',
    metavar='VERSION',
    type=str,
    help="set version (no git commits)",
)


def main():
    args = parser.parse_args()

    if args.set:
        vers_from_str(args.set)
        write_vfile(args.set)
        exit()

    release = args.release

    major, minor, rev, build = vers_from_str(CVERS)

    if release == 'major':
        major += 1
        minor = 0
        rev = 0
    elif release == 'minor':
        minor += 1
        rev = 0
    elif release == 'rev':
        rev += 1

    version = '{}.{}.{}'.format(major, minor, rev)

    try:
        resp = input("new {} release: {} -> {}\ntype 'yes' to confirm: ".format(release, CVERS, version))
        if resp != 'yes':
            exit("abort.")
    except KeyboardInterrupt:
        exit("\nabort.")

    tags = subprocess.run(['git', 'tag'], capture_output=True, text=True).stdout.split()
    if version in tags:
        exit("git tag already exists for '{}'; aborting.".format(version))

    logging.info("updating to vfile {}...".format(VFILE))
    write_vfile(version)

    msg = "new {} release {}".format(release, version)

    repo = git.Repo()
    logging.info("git commit...")
    repo.git.commit('-m', msg, VFILE)
    logging.info("git tag '{}'...".format(version))
    repo.git.tag('-m', msg, version)

    logging.info("generating sdist and wheel...")
    out = subprocess.run(
        [sys.executable, 'setup.py', 'sdist', 'bdist_wheel'],
        check=True,
        capture_output=True,
        text=True,
    )
    logging.debug(out.stdout.strip())

    logging.info("update to dev version...")
    dvers = version + '+dev0'
    write_vfile(dvers)
    repo.git.commit('-m', "post release dev versioning", VFILE)


if __name__ == '__main__':
    main()
