#!/usr/bin/perl
use strict;
#use warnings;

use Cwd;
use Getopt::Long qw(:config auto_help);

my $CVSROOT="anoncvs\@mirror.planetunix.net:/cvs";
my $ARCH="i386"; ## Generalize this by the output of `machine`

my @build_array = ();

my @build_kernel_array = (
    # Build kernel
    { name => "cd_confdir", command => "cd /usr/src/sys/arch/$ARCH/conf" },
    { name => "run_config", command => "/usr/sbin/config GENERIC" },
    { name => "cd_compiledir", command => "cd /usr/src/sys/arch/$ARCH/compile/GENERIC" },
    { name => "run_makeclean", command => "make clean" },
    { name => "run_makedepend", command => "make depend" },
    { name => "run_make", command => "make" },
    { name => "run_makeinstall", command => "make install" },
    );

my @build_userland_array = (
    # Build userland
    { name => "clean_objdir", command => "rm -rf /usr/obj/*" },
    { name => "cd_usrsrc", command => "cd /usr/src" },
    { name => "run_makeobj", command => "make obj" },
    { name => "cd_usrsrcetc", command => "cd /usr/src/etc" },
    { name => "run_makedistribdirs", command => "env DESTDIR=/ make distrib-dirs" },
    { name => "cd_usrsrc", command => "cd /usr/src" },
    { name => "run_makebuild", command => "make build" },
    );

sub run_command {
    my $command_name = $_[0];
    my $command_path = $_[1];
    print "In run_command block. Name: $command_name, Command: $command_path\n";
    system($command_path) == 0 or die "\nFailure at step: $command_name, Exit status: $?\n"
};

sub update_cvs {
    if (-d "/usr/src") {
        print "Source checkout exists, updating files\n";
        chdir("/usr/src");
        system("/usr/bin/cvs up -rOPENBSD_4_8 -Pd");
    }
    else {
        print "Source checkout does not exist. Checking out from CVS repo.\n";
        chdir("/usr");
        system("/usr/bin/cvs -d$CVSROOT checkout -rOPENBSD_4_8 -P src");
    }
};

sub main {
    # Command line parameters
    my %options = {};
    GetOptions(
        'skipcvs' => \$options{'skipcvs'},
        'kernel' => \$options{'build_kernel'},
        'userland' => \$options{'build_userland'},
        );

    if (defined($options{'skipcvs'})) {
        print "Requested to skip updating OpenBSD source.\n";
    }
    else {
        print "Updating source CVS tree\n";
        &update_cvs;
    }

    if (defined($options{'build_kernel'})) {
        print "Building kernel\n";
        push @build_array, @build_kernel_array;
    }

    if (defined($options{'build_userland'})) {
        print "Building userland\n";
        push @build_array, @build_userland_array;
    }

    for my $current ( 0 .. $#build_array) {
        print "$build_array[$current]{name}\n";
    }

    die 1;

    for my $current (0 ... $#build_array) {
        &run_command($build_array[$current]{name}, $build_array[$current]{command});
    }
    
    print "Build complete.";
    exit 0;
};

&main;
