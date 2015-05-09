#!/bin/sh -x

export DESTDIR=/usr/build/dest
export RELEASEDIR=/usr/build/rel

echo "Clearing out your old build and release directories."
rm -rf $DESTDIR
rm -rf $RELEASEDIR

echo "Setting up your build and release directories."
mkdir -p $DESTDIR $RELEASEDIR

echo "Building the Release"
cd /usr/src/etc
make release

echo "Verifying the files are built and as they should."
cd /usr/src/distrib/sets
sh checkflist
cd $RELEASEDIR
ls -l > $RELEASEDIR/index.txt
