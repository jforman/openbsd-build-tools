#!/bin/sh -x

function check_exit {
if [ "$1" -eq "0" ]; then
    echo "$2 exited without problem."
    return 0
else
    echo "There was a problem. Failure step: $2"
    return 1
fi

}
CVSROOT=anoncvs@mirror.osn.de:/cvs #anoncvs@obsd.cec.mtu.edu:/cvs

if [ "$1" == "skipcvs" ]; then
    echo "Skipping grabbing new source via CVS"
else
    if [ -d "/usr/src" ]; then
        echo "Updating source checkout in /usr/src"
        cd /usr/src/
        cvs up -rOPENBSD_4_8 -Pd
    else
        echo "Source code checkout does not exist. Checking out release"
        cd /usr
        cvs -d$CVSROOT checkout -rOPENBSD_4_8 -P src
    fi
fi

# building the kernel
cd /usr/src/sys/arch/i386/conf
/usr/sbin/config GENERICf

#check_exit $? "Config GENERIC"

## This is where it all breaks down. 
## Shell scripts don't give us enough functionality to make this elegant.
if [ "`check_exit $? \"Config GENERIC\"`" -ne "0" ]; then
    exit 1
else
    "config generic succeeded"
fi



cd ../compile/GENERIC

make clean && make depend && make

if [ "$?" -eq "0" ]; then
    echo "Config GENERIC exited without problem."
else
    echo "There was a problem with the config step."
    exit 1
fi


echo "exit status from make clean/depend/make: $?"

exit 0

### stop here

make install

# building the userland
rm -rf /usr/obj/*
cd /usr/src
make obj

if [ "$?" -eq "0" ]; then
    echo "exit status is 0"
else
    echo "exit is non zero"
fi

cd /usr/src/etc && env DESTDIR=/ make distrib-dirs

cd /usr/src
make build
