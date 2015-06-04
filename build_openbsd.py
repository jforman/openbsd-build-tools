#!/usr/bin/env python
"""Wrapper for updating, building, and creating OpenBSD releases."""

import argparse
import collections
import datetime
import os
import platform
import re
import subprocess
import sys
import tarfile

BUILD_LOG = collections.OrderedDict()


class BuildException(Exception):
    """Exception class to handle errors in the build proces."""
    pass


class RunCommandError(Exception):
    """Exception class to handle errors when a shell command is run."""
    pass


def get_kernel_name():
    """ Return the currently-running kernel name and build number."""
    kernel_name = run_command("/usr/bin/uname -v", return_output=True).split("#")[0]
    return kernel_name


def get_cpu_count():
    """ Return the number of CPUs OpenBSD is using."""
    cpu_count = int(run_command("/sbin/sysctl -n hw.ncpu",
                                return_output=True))
    return cpu_count


def get_running_branch():
    """ Return currently-running branch of installed OS."""
    branch = run_command("/usr/bin/uname -r", return_output=True)
    if not re.match(r'\d\.\d', branch):
        raise BuildException("Unable to determine running branch, "
                             "expected format \d.\d: %s" % branch)

    log_build_action("Branch found to be %s." % branch)
    return branch.replace(".", "").strip()


def parse_args():
    """Process arguments from command line."""
    parser = argparse.ArgumentParser(description="Build and install OpenBSD kernel, userland, and releases.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--build",
                        action="append",
                        choices=["kernel", "userland", "release"],
                        help="Which part of OpenBSD to build.")
    parser.add_argument("--cpus",
                        default=get_cpu_count(),
                        help="Number of CPU threads to pass to make. Auto-detected.")
    parser.add_argument("--cvs_tag",
                        help="Tag to checkout/update. Example: OPENBSD_5_5",
                        default="HEAD")
    parser.add_argument("--cvs_server",
                        default="openbsd.cs.toronto.edu",
                        help="FQDN/IP address of CVS server for OpenBSD repo.")
    parser.add_argument("--force",
                        action="store_true",
                        help="Some steps tend to fail. Force ignores those failures. Applies to: checkflist.")
    parser.add_argument("-i", "--interactive",
                        action="store_true",
                        help="If an error occurs, pause for user decision of whether to continue.")
    parser.add_argument("--kernel",
                        choices=set(["GENERIC",
                                     "GENERIC.MP",
                                     "RAMDISK",
                                     "RAMDISK_CD",
                                     get_kernel_name()]),
                        default=get_kernel_name(), help="Name of kernel to build.")
    parser.add_argument("--platform",
                        default=platform.machine(),
                        help="Machine platform. Auto-detected. Normally you won't need to redefine this.")
    parser.add_argument("--update_cvs",
                        action="store_true",
                        help="Checkout/update the local CVS checkout.")
    parser.add_argument("--release_base",
                        default="/usr/release",
                        help="Base directory on local file system where a release is built.")
    parser.add_argument("--site_base",
                        default=None,
                        help="Directory from which site tarball is created.")

    args = parser.parse_args()
    return args


def log_build_action(action):
    """Append build actions to OrderedDict BUILD_LOG."""
    now = datetime.datetime.now()
    print "Build Action: %s" % action
    BUILD_LOG[now] = action

def get_user_choice():
    """Process y/n input from the user."""
    prompt = "Continue [y,n]? "
    result = raw_input(prompt).lower()
    if result == "y":
        log_build_action("User choice presented. User selected true.")
        return True

    log_build_action("User choice presented. User selected false.")
    return False

def run_command(command_path, return_output=False, force=False,
                interactive=False):
    """Execute passed command line."""

    log_build_action("Running command: %s" % command_path)
    try:
        # TODO(jforman): This logic is cludgy, but seems there is no
        # subprocess method flexible enough to watch output and/or
        # return output at the same time, without buffering everything.
        if return_output:
            return subprocess.check_output(command_path, shell=True)
        else:
            subprocess.check_call(command_path, shell=True)
    except OSError, err:
        log_build_action("OSError Exception in run_command: %s" % err)
        raise RunCommandError
    except subprocess.CalledProcessError, err:
        log_build_action("CalledProcessError in run_command: %s" % err)
        if force:
            log_build_action("FORCE ENABLED, CONTINUING PAST ERROR.")
            return
        if interactive:
            if get_user_choice():
                return

        raise RunCommandError

def read_cvs_tag():
    """Attempt to read the branch name from a CVS repo checkout."""

    try:
        with open("/usr/src/CVS/Tag") as tag_fh:
            cvs_tag = tag_fh.readline()[1:].strip()
    except IOError, err:
        log_build_action("Unable to read CVS tag from disk: %s" % err)
        raise

    return cvs_tag

def checkout_or_update_cvs(cvs_tag, cvs_server):
    """Manage a CVS repository checkout."""
    cvs_tag_options = ""
    cvs_server_path = "anoncvs@%s:/cvs" % cvs_server

    if not (os.access("/usr/", os.W_OK) or os.access("/usr/src", os.W_OK)):
        log_build_action("Not enough write permissions to checkout/update "
                         "local CVS checkout in /usr/src.")
        raise RunCommandError

    if cvs_tag is not None:
        cvs_tag_options = "-r%s" % cvs_tag

    if not os.path.exists("/usr/src/CVS/Tag"):
        log_build_action("No CVS checkout found. Attempting checkout now.")
        os.chdir("/usr")
        run_command("/usr/bin/cvs -d %(cvs_server_path)s checkout "
                    "%(cvs_tag_options)s -P src" % {"cvs_server_path" : cvs_server_path,
                                                    "cvs_tag_options" : cvs_tag_options})
        return

    local_cvs_tag = read_cvs_tag()
    if cvs_tag and (local_cvs_tag != cvs_tag):
        log_build_action("Upgrading across versions via source "
                         "is not suggested.")
        log_build_action("See: http://www.openbsd.org/faq/faq5.html#BldBinary")
        raise RunCommandError

    log_build_action("CVS checkout found for branch %(branch)s. "
                     "Executing update." % {"branch" : local_cvs_tag})
    os.chdir("/usr/src/")
    run_command("/usr/bin/cvs -d %(cvs_server_path)s up "
                "%(cvs_tag)s -Pd" % {"cvs_server_path" : cvs_server_path,
                                     "cvs_tag" : cvs_tag_options})


def build_and_install_kernel(platform, kernel, cpus):
    """Manage building and installing an OpenBSD kernel."""
    log_build_action("Building kernel %(kernel)s for "
                     "%(platform)s" % {"kernel" : kernel,
                                       "platform" : platform})
    os.chdir("/usr/src/sys/arch/%(platform)s/conf" % {"platform" : platform})
    run_command("/usr/sbin/config %(kernel)s" % {"kernel" : kernel})
    os.chdir("/usr/src/sys/arch/%(platform)s/"
             "compile/%(kernel)s" % {"platform" : platform,
                                     "kernel" : kernel})
    run_command("/usr/bin/make -j%d clean" % cpus)
    run_command("/usr/bin/make -j%d" % cpus)
    run_command("/usr/bin/make -j%d install"% cpus)
    log_build_action("Kernel build complete.")


def build_and_install_userland(cpus):
    """ Iterate through steps to build and install userland."""
    log_build_action("Building userland.")
    run_command("/bin/rm -rf /usr/obj/*")
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%d obj" % cpus)
    os.chdir("/usr/src/etc")
    run_command("/usr/bin/env DESTDIR=/ /usr/bin/make "
                "-j%d distrib-dirs" % cpus)
    os.chdir("/usr/src")
    run_command("/usr/bin/make -j%d build" % cpus)
    log_build_action("Userland build complete.")

def build_release(release_base, site_base, force, interactive):
    """Build release set of installable OpenBSD files."""
    log_build_action("Setting build environment variables.")
    os.environ['DESTDIR'] = "%s/dest" % release_base
    os.environ['RELEASEDIR'] = "%s/release" % release_base

    log_build_action("Clearing out old build and release directories.")
    run_command("/bin/rm -rf %s" % os.environ['DESTDIR'])
    run_command("/bin/rm -rf %s" % os.environ['RELEASEDIR'])
    log_build_action("Creating clean build and release directories.")
    run_command("/bin/mkdir -p %s" % os.environ['DESTDIR'])
    run_command("/bin/mkdir -p %s" % os.environ['RELEASEDIR'])
    log_build_action("Building release.")
    os.chdir("/usr/src/etc")
    run_command("/usr/bin/make release")
    if site_base:
        build_site_tarball(os.environ['RELEASEDIR'], site_base)

    log_build_action("Verifying release.")
    os.chdir("/usr/src/distrib/sets")
    run_command("/bin/sh checkflist", force=force)
    os.chdir(os.environ['RELEASEDIR'])
    log_build_action("Generating releaese index.")
    run_command("/bin/ls -nT > %s/index.txt" % os.environ['RELEASEDIR'])

def build_site_tarball(release_dir, site_base):
    """Build a siteXX.tgz containing custom files to deploy."""
    log_build_action("Building site tarball rooted at %s" % site_base)
    site_targz = tarfile.open(name="%s/site%s.tgz" % (release_dir, get_running_branch()),
                              mode="w:gz",)
    site_targz.add(site_base, arcname="/", recursive=True)
    site_targz.close()

def main():
    """Build while you build, so you can secure while you're secure."""
    os.unsetenv("DESTDIR")
    os.unsetenv("RELEASEDIR")
    args = parse_args()
    log_build_action("Command line args: %s" % args)
    log_build_action("Build started.")

    try:
        if args.update_cvs:
            checkout_or_update_cvs(args.cvs_tag, args.cvs_server)
        if args.build and "kernel" in args.build:
            build_and_install_kernel(args.platform, args.kernel, args.cpus)
        if args.build and "userland" in args.build:
            build_and_install_userland(args.cpus)
        if args.build and "release" in args.build:
            build_release(args.release_base, args.site_base, args.force, args.interactive)
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
        print "Environment at time of failure: %s" % os.environ
        sys.exit(1)
