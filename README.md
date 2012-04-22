# OpenBSD Tools

# Purpose

Contained in this repository are various scripts, config files, and other handy code
I have generated over the years of running OpenBSD (mostly as a firewall/router/jack-of-all-trades server)
for my home network.

# Included Tools

## build-openbsd.py

This is a wrapper for building the OpenBSD source code, both kernel and userland binaries.

It also includes functionality to checkout and update a CVS respository.

### Dependencies

* Python (at least 2.7 due to use of argparse)
* Enough disk space to checkout source from CVS and build binaries. (comp${release}.tgz)

### Operation

These commands are all expected to be run as root, our via Sudo.

#### Updating local CVS checkout

    # ./build-openbsd.py --updatecvs
    ...
    ---------- Actions Attempted
    2012-04-22 11:36:07.324283 Build started.
    2012-04-22 11:36:07.327844 Command line args: Namespace(build=None, cvstag=None, kernel='GENERIC', updatecvs=True)
    2012-04-22 11:36:07.329382 CVS checkout found. Executing update.
    2012-04-22 11:36:07.330051 /usr/bin/cvs -d anoncvs@anoncvs3.usa.openbsd.org:/cvs up -Pd
    2012-04-22 11:51:46.769257 Process Call Output: 0
    2012-04-22 11:51:46.771714 Build completed.

### Building the kernel

    # ./build-openbsd.py --build kernel --kernel GENERIC.MP 
    ...
    ---------- Actions Attempted
    2012-04-22 13:12:25.446923 Build started.
    2012-04-22 13:12:25.451764 Command line args: Namespace(build=['kernel'], cvstag=None, kernel='GENERIC.MP', updatecvs=False)
    2012-04-22 13:12:25.452109 Building kernel GENERIC.MP for amd64
    2012-04-22 13:12:25.487174 /usr/sbin/config GENERIC.MP
    2012-04-22 13:12:26.588577 Process Call Output: 0
    2012-04-22 13:12:26.591497 /usr/bin/make -j3 clean
    2012-04-22 13:12:26.943346 Process Call Output: 0
    2012-04-22 13:12:26.945219 /usr/bin/make -j3
    2012-04-22 13:20:05.859982 Process Call Output: 0
    2012-04-22 13:20:05.862780 /usr/bin/make -j3 install
    2012-04-22 13:20:07.423744 Process Call Output: 0
    2012-04-22 13:20:07.424923 Kernel build complete.
    2012-04-22 13:20:07.425284 Build completed.

### Building userland

    # ./build-openbsd.py --build userland 
    ...
    ---------- Actions Attempted
    2012-04-22 13:46:04.839990 Build started.
    2012-04-22 13:46:04.844133 Command line args: Namespace(build=['userland'], cvstag=None, kernel='GENERIC', updatecvs=False)
    2012-04-22 13:46:04.844376 Building userland.
    2012-04-22 13:46:04.844554 /bin/rm -rf /usr/obj/*
    2012-04-22 13:47:18.644642 Process Call Output: 0
    2012-04-22 13:47:18.647133 /usr/bin/make -j3 obj
    2012-04-22 13:51:13.776190 Process Call Output: 0
    2012-04-22 13:51:13.780323 /usr/bin/env DESTDIR=/ /usr/bin/make -j3 distrib-dirs
    2012-04-22 13:51:15.334464 Process Call Output: 0
    2012-04-22 13:51:15.337171 /usr/bin/make -j3 build
    2012-04-22 17:06:06.967311 Process Call Output: 0
    2012-04-22 17:06:06.969534 Userland build complete.
    2012-04-22 17:06:06.969897 Build completed.

## build-release.sh

This shell script just collects the commands for creating a release of OpenBSD.

It expects a fully built kernel and userland in /usr/src

### Operation

Simply run 'build-release.sh'

The directory used for collecting the necessary files is /usr/build/dest, the destination directory.

The directory that will be the final destination for installation files is /usr/build/rel, the release directory.

The release directory is what should be published to your local FTP or HTTP server for access by install clients.
