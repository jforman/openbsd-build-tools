#!/usr/bin/env python

"""Wrapper around updating and building OpenBSD source.
# ./build-openbsd.py --help                                                                                                 
usage: build-openbsd.py [-h] [--build {kernel,userland}]
                        [--kernel {GENERIC,GENERIC.MP,RAMDISK,RAMDISK_CD}]

Wrapper around building OpenBSD kernel and userland.

optional arguments:
  -h, --help            show this help message and exit
  --build {kernel,userland}
                        What to build: kernel or userland.
  --kernel {GENERIC,GENERIC.MP,RAMDISK,RAMDISK_CD}
                        Name of kernel to build.
"""

import argparse
import collections
import datetime
import os
import platform
import subprocess
import sys

BUILD_LOG = collections.OrderedDict()
NUM_CPUS = 3
PLATFORM = platform.machine()

class BuildException(Exception):
    """Exception class to handle errors in the build proces."""
    pass

class RunCommandError(Exception):
    """Exception class to handle errors when a shell command is run."""
    pass

def parse_args():
    """Process arguments from command line."""
    parser = argparse.ArgumentParser(description="Wrapper around building OpenBSD kernel and userland.")
    parser.add_argument("--build", choices=["kernel", "userland"], help="What to build: kernel or userland.")
    parser.add_argument("--kernel", choices=["GENERIC", "GENERIC.MP", "RAMDISK", "RAMDISK_CD"],
                        default="GENERIC", help="Name of kernel to build.")
    args = parser.parse_args()
    return args


def log_build_action(action):
    """Append build actions to OrderedDict BUILD_LOG."""
    now = datetime.datetime.now()
    BUILD_LOG[now] = action


def run_command(command_path):
    """Execute passed command line."""
    print "Executing: %s" % command_path
    log_build_action(command_path)
    try:
        process_call = subprocess.check_call(command_path, shell=True)
    except OSError, err:
        print "OSError Exception in run_command: %s" % err
        raise RunCommandError
    except subprocess.CalledProcessError, err:
        print "CalledProcessError in run_command: %s" % err
        raise RunCommandError

    print "Process Call Output: %s" % process_call

def build_and_install_kernel(args):
    """ Iterate through steps to build and install kernel."""
    print "Building kernel %(kernel)s for %(platform)s" % {"kernel" : args.kernel,
                                                           "platform" : PLATFORM }

    os.chdir("/usr/src/sys/arch/%(platform)s/conf" % {"platform" : PLATFORM })
    run_command("/usr/sbin/config %(kernel)s" % { "kernel" : args.kernel })
    os.chdir("/usr/src/sys/arch/%(platform)s/compile/%(kernel)s" % { "platform" : PLATFORM,
                                                                     "kernel" : args.kernel })
    run_command("/usr/bin/make -j%(cpus)d clean" % { "cpus" : NUM_CPUS })
    run_command("/usr/bin/make -j%(cpus)d depend" % { "cpus" : NUM_CPUS })
    run_command("/usr/bin/make -j%(cpus)d" % { "cpus" : NUM_CPUS })
    run_command("/usr/bin/make -j%(cpus)d install"% { "cpus" : NUM_CPUS })


def build_and_install_userland(args):
    """ Iterate through steps to build and install userland."""
    print "Building userland."
    run_command("/bin/rm -rf /usr/obj/*")
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%(cpus)d obj" % { "cpus" : NUM_CPUS })
    os.chdir("/usr/src/etc")
    run_command("/usr/bin/env DESTDIR=/ /usr/bin/make -j%(cpus)d distrib-dirs" % { "cpus" : NUM_CPUS })
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%(cpus)d build" % { "cpus" : NUM_CPUS })
    
def main():
    """Build while you build, so you can secure while you're secure."""
    args = parse_args()
    
    try:
        if args.build == "kernel":
            build_and_install_kernel(args)
        if args.build == "userland":
            build_and_install_userland(args)
    except OSError, err:
        print "Exception! OSError: %s" % err
        raise BuildException
    except RunCommandError:
        raise BuildException
    except KeyboardInterrupt:
        print "User requested process killed."
    finally:
        print "---------- Actions Attempted"
        for log_time, log_action in BUILD_LOG.items():
            print log_time, log_action


if __name__ == "__main__":
    try:
        main()
    except BuildException:
        print "BuildException"
        sys.exit(1)
