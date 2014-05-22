#!/usr/bin/env python
"""Wrapper around updating, building, and installing updated
OpenBSD source code.

Provides the ability to update the installed machine's branch code,
hopefully to STABLE.

Otherwise, allows for automated following of CURRENT.
"""

import argparse
import collections
import datetime
import os
import platform
import subprocess
import sys

BUILD_LOG = collections.OrderedDict()
CVS_SERVER_PATH = "anoncvs@openbsd.cs.toronto.edu:/cvs"
CVS_TAG = "/usr/src/CVS/Tag"
PLATFORM = platform.machine()

class BuildException(Exception):
    """Exception class to handle errors in the build proces."""
    pass

class RunCommandError(Exception):
    """Exception class to handle errors when a shell command is run."""
    pass


def determine_cpu_count():
    """ Return the number of CPUs OpenBSD is using."""
    cpu_count = int(run_command("/sbin/sysctl -n hw.ncpu", return_output = True))
    return cpu_count

def determine_running_kernel():
    """ Return the currently-running kernel name and build number."""
    (kernel_name, build_number) = run_command("/usr/bin/uname -v", return_output = True).split("#")
    return kernel_name, build_number


def parse_args():
    """Process arguments from command line."""
    running_kernel = determine_running_kernel()[0]
    parser = argparse.ArgumentParser(description="Build and install OpenBSD kernel and userland.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--build",
                        action="append",
                        choices=["kernel", "userland"],
                        help="What to build: kernel and/or userland.")
    parser.add_argument("--updatecvs",
                        action="store_true",
                        help="Checkout/update the local CVS check out.")
    parser.add_argument("--cvstag",
                        help="Tag to checkout/update. Example: OPENBSD_5_5")
    parser.add_argument("--kernel",
                        choices=set(["GENERIC",
                                     "GENERIC.MP",
                                     "RAMDISK",
                                     "RAMDISK_CD",
                                     running_kernel]),
                        default=running_kernel, help="Name of kernel to build.")
    args = parser.parse_args()
    return args


def log_build_action(action):
    """Append build actions to OrderedDict BUILD_LOG."""
    now = datetime.datetime.now()
    print "Build Action: %s" % action
    BUILD_LOG[now] = action


def run_command(command_path, return_output = False):
    """Execute passed command line."""
    log_build_action("Running command: %s" % command_path)
    try:
        # TODO(jforman): This logic is cludgy, but seems there is no
        # subprocess method flexible enough to watch output and/or
        # return output at the same time, without buffering everything.
        if return_output:
            return_output = subprocess.check_output(command_path, shell=True)
        else:
            subprocess.check_call(command_path, shell=True)
    except OSError, err:
        log_build_action("OSError Exception in run_command: %s" % err)
        raise RunCommandError
    except subprocess.CalledProcessError, err:
        log_build_action("CalledProcessError in run_command: %s" % err)
        raise RunCommandError

    if return_output:
        return return_output

def read_cvs_tag():
    """Attempt to read the branch name from a CVS repo checkout."""

    try:
        with open(CVS_TAG) as tag_fh:
            cvs_tag = tag_fh.readline()[1:].strip()
    except IOError, err:
        log_build_action("Unable to read CVS tag from disk: %s" % err)
        raise

    return cvs_tag

def checkout_or_update_cvs(args):
    """Handle either checking out or updating an already 
    retrieved CVS repository."""
    cvs_tag_options = ""

    if not (os.access("/usr/", os.W_OK) or os.access("/usr/src", os.W_OK)):
        log_build_action("Not enough write permissions to checkout/update "
                         "local CVS checkout in /usr/src.")
        raise RunCommandError

    if args.cvstag is not None:
        cvs_tag_options = "-r%(cvs_tag)s" % { "cvs_tag" : args.cvstag }

    if not os.path.exists(CVS_TAG):
        log_build_action("No CVS checkout found. Attempting checkout now.")
        os.chdir("/usr")
        run_command("/usr/bin/cvs -d %(cvs_server_path)s checkout "
                    "%(cvs_tag)s -P src" % { "cvs_server_path" : CVS_SERVER_PATH,
                                             "cvs_tag" : cvs_tag_options })
        return

    local_cvs_tag = read_cvs_tag()
    if args.cvstag and (local_cvs_tag != args.cvstag):
        log_build_action("Upgrading across versions via source "
                         "is not suggested.")
        log_build_action("See: http://www.openbsd.org/faq/faq5.html#BldBinary")
        raise RunCommandError

    log_build_action("CVS checkout found for branch %(branch)s. "
                     "Executing update." % {"branch" : local_cvs_tag})
    os.chdir("/usr/src/")
    run_command("/usr/bin/cvs -d %(cvs_server_path)s up "
                "%(cvs_tag)s -Pd" % { "cvs_server_path" : CVS_SERVER_PATH,
                                      "cvs_tag" : cvs_tag_options })


def build_and_install_kernel(args, env):
    """ Iterate through steps to build and install kernel."""
    log_build_action("Building kernel %(kernel)s for "
                     "%(platform)s" % {"kernel" : args.kernel,
                                       "platform" : PLATFORM })
    os.chdir("/usr/src/sys/arch/%(platform)s/conf" % {"platform" : PLATFORM })
    run_command("/usr/sbin/config %(kernel)s" % { "kernel" : args.kernel })
    os.chdir("/usr/src/sys/arch/%(platform)s/"
             "compile/%(kernel)s" % { "platform" : PLATFORM,
                                      "kernel" : args.kernel })
    run_command("/usr/bin/make -j%(NUM_CPUS)d clean" % env)
    run_command("/usr/bin/make -j%(NUM_CPUS)d" % env)
    run_command("/usr/bin/make -j%(NUM_CPUS)d install"% env)
    log_build_action("Kernel build complete.")


def build_and_install_userland(env):
    """ Iterate through steps to build and install userland."""
    log_build_action("Building userland.")
    run_command("/bin/rm -rf /usr/obj/*")
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%(NUM_CPUS)d obj" % env)
    os.chdir("/usr/src/etc")
    run_command("/usr/bin/env DESTDIR=/ /usr/bin/make "
                "-j%(NUM_CPUS)d distrib-dirs" % env)
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%(NUM_CPUS)d build" % env)
    log_build_action("Userland build complete.")
    
def main():
    """Build while you build, so you can secure while you're secure."""
    args = parse_args()
    env = {}
    env["NUM_CPUS"] = determine_cpu_count()
    log_build_action("Command line args: %s" % args)
    log_build_action("Environment: %s" % env)

    log_build_action("Build started.")
    
    try:
        if args.updatecvs:
            checkout_or_update_cvs(args)
        if args.build and "kernel" in args.build:
            build_and_install_kernel(args, env)
        if args.build and "userland" in args.build:
            build_and_install_userland(env)
        log_build_action("Build completed.")
    except OSError, err:
        log_build_action("Exception! OSError: %s" % err)
        raise BuildException
    except RunCommandError:
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
