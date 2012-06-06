#!/usr/bin/env python

"""Wrapper around updating and building OpenBSD source.
# ./build-openbsd.py --help
usage: build-openbsd.py [-h] [--build {kernel,userland}] [--updatecvsrepo]
                        [--cvstag CVSTAG]
                        [--kernel {GENERIC,GENERIC.MP,RAMDISK,RAMDISK_CD}]

Wrapper to build OpenBSD kernel and userland. Also can update local CVS repo.

optional arguments:
  -h, --help            show this help message and exit
  --build {kernel,userland}
                        What to build: kernel and/or userland.
  --updatecvsrepo       Whether to checkout/update local CVS repository of
                        code.
  --cvstag CVSTAG       Tag name to checkout/update. No tag means HEAD.
                        Example: OPENBSD_5_0
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
CVS_SERVER_PATH = "anoncvs@anoncvs3.usa.openbsd.org:/cvs"
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
    parser = argparse.ArgumentParser(description="Wrapper to build OpenBSD kernel and userland. Also can update local CVS repo.")
    parser.add_argument("--build", action="append", choices=["kernel", "userland"], help="What to build: kernel and/or userland.")
    parser.add_argument("--updatecvs", action="store_true", help="Whether to checkout/update local CVS repository of code.")
    parser.add_argument("--cvstag", help="Tag name to checkout/update. No tag means HEAD. Example: OPENBSD_5_0")
    parser.add_argument("--kernel", choices=["GENERIC", "GENERIC.MP", "RAMDISK", "RAMDISK_CD"],
                        default="GENERIC", help="Name of kernel to build.")
    args = parser.parse_args()
    return args


def log_build_action(action):
    """Append build actions to OrderedDict BUILD_LOG."""
    now = datetime.datetime.now()
    print action
    BUILD_LOG[now] = action


def run_command(command_path):
    """Execute passed command line."""
    print "Executing: %s" % command_path
    log_build_action(command_path)
    try:
        process_call = subprocess.check_call(command_path, shell=True)
    except OSError, err:
        log_build_action("OSError Exception in run_command: %s" % err)
        raise RunCommandError
    except subprocess.CalledProcessError, err:
        log_build_action("CalledProcessError in run_command: %s" % err)
        raise RunCommandError

    log_build_action("Process Call Output: %s" % process_call)

def read_cvs_tag():
    """Attempt to read the branch name from a CVS repo checkout."""
    with open("/usr/src/CVS/Tag") as tag_fh:
        cvs_tag = tag_fh.readline()[1:].strip()

    return cvs_tag

def checkout_or_update_cvs(args):
    """Handle either checking out or updating an already retrieved CVS repository."""
    cvs_tag_options = ""

    if not (os.access("/usr/", os.W_OK) or os.access("/usr/src", os.W_OK)):
        log_build_action("Not enough write permissions to checkout/update local CVS checkout in /usr/src.")
        raise RunCommandError

    if args.cvstag:
        cvs_tag_options = "-r%(cvs_tag)s" % { "cvs_tag" : args.cvstag }

    if not os.path.exists("/usr/src/CVS/Tag"):
        log_build_action("No CVS checkout found. Attempting checkout now.")
        os.chdir("/usr")
        run_command("/usr/bin/cvs -d %(cvs_server_path)s checkout %(cvs_tag)s -P src" % { "cvs_server_path" : CVS_SERVER_PATH,
                                                                                                "cvs_tag" : cvs_tag_options })
    else:
        log_build_action("CVS checkout found. Executing update.")
        local_cvs_tag = read_cvs_tag()
        if (args.cvstag is not None) and args.cvstag != local_cvs_tag:
            log_build_action("The tag you requested (%(user_cvs_tag)s) does not match what is locally checked out (%(local_cvs_tag)s). Exiting" %
                             { "user_cvs_tag" : args.cvstag,
                               "local_cvs_tag" : local_cvs_tag })
            raise BuildException
        os.chdir("/usr/src/")
        run_command("/usr/bin/cvs -d %(cvs_server_path)s up -Pd" % { "cvs_server_path" : CVS_SERVER_PATH })


def build_and_install_kernel(args):
    """ Iterate through steps to build and install kernel."""
    log_build_action("Building kernel %(kernel)s for %(platform)s" % {"kernel" : args.kernel,
                                                                      "platform" : PLATFORM })

    os.chdir("/usr/src/sys/arch/%(platform)s/conf" % {"platform" : PLATFORM })
    run_command("/usr/sbin/config %(kernel)s" % { "kernel" : args.kernel })
    os.chdir("/usr/src/sys/arch/%(platform)s/compile/%(kernel)s" % { "platform" : PLATFORM,
                                                                     "kernel" : args.kernel })
    run_command("/usr/bin/make -j%(cpus)d clean" % { "cpus" : NUM_CPUS })
    run_command("/usr/bin/make -j%(cpus)d" % { "cpus" : NUM_CPUS })
    run_command("/usr/bin/make -j%(cpus)d install"% { "cpus" : NUM_CPUS })
    log_build_action("Kernel build complete.")


def build_and_install_userland(args):
    """ Iterate through steps to build and install userland."""
    log_build_action("Building userland.")
    run_command("/bin/rm -rf /usr/obj/*")
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%(cpus)d obj" % { "cpus" : NUM_CPUS })
    os.chdir("/usr/src/etc")
    run_command("/usr/bin/env DESTDIR=/ /usr/bin/make -j%(cpus)d distrib-dirs" % { "cpus" : NUM_CPUS })
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%(cpus)d build" % { "cpus" : NUM_CPUS })
    log_build_action("Userland build complete.")
    
def main():
    """Build while you build, so you can secure while you're secure."""
    args = parse_args()
    log_build_action("Build started.")
    log_build_action("Command line args: %s" % args)
    
    try:
        if args.updatecvs:
            checkout_or_update_cvs(args)
        if args.build and "kernel" in args.build:
            build_and_install_kernel(args)
        if args.build and "userland" in args.build:
            build_and_install_userland(args)
        log_build_action("Build completed.")
    except OSError, err:
        log_build_action("Exception! OSError: %s" % err)
        raise BuildException
    except RunCommandError:
        raise BuildException
    except ExecutionError:
        raise BuildException
    except KeyboardInterrupt:
        log_build_action("User requested process killed.")
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
