#!/usr/bin/perl

use Cwd;

$CVSROOT="anoncvs@mirror.planetunix.net:/cvs";
$ARCH="i386"; ## Generalize this by the output of `machine`

@commands_array = (
    # Build kernel
    { name => "cd_confdir", command => "cd /usr/src/sys/arch/$ARCH/conf" },
    { name => "run_config", command => "/usr/sbin/config GENERIC" },
    { name => "cd_compiledir", command => "cd /usr/src/sys/arch/$ARCH/compile/GENERIC" },
    { name => "run_makeclean", command => "make clean" },
    { name => "run_makedepend", command => "make depend" },
    { name => "run_make", command => "make" },
    { name => "run_makeinstall", command => "make install" },
    ## Reboot here. # Throw in a -postreboot argument?
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
    print "\n";
    $command_name = $_[0];
    $command_path = $_[1];
    print "name: $command_name\n";
    print "running: $command_path\n";
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
    if ($ARGV[0] eq "skipcvs") {
        print "Source upgrade via CVS skipped.\n";
    }
    else {
        &update_cvs;
    }

    for $current (0 ... $#commands_array) {
        &run_command($commands_array[$current]{name}, $commands_array[$current]{command});
    }
    
    print "Build complete."
    exit 0
};

&main;
