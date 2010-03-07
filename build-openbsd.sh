#!/bin/sh

cd /usr/src
cvs -q up -rOPENBSD_4_6 -Pd

# building the kernel
cd /usr/src/sys/arch/i386/conf
config GENERIC
cd ../compile/GENERIC
make clean && make depend && make
make install

# building the userland
rm -rf /usr/obj/*
cd /usr/src
make obj

cd /usr/src/etc && env DESTDIR=/ make distrib-dirs

cd /usr/src
make build