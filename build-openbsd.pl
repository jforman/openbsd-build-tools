#!/usr/bin/perl
use strict;
#use warnings;

use Cwd;
use Getopt::Long qw(:config auto_help);

my $CVSROOT="anoncvs\@mirror.planetunix.net:/cvs";
my $ARCH="amd64"; ## Generalize this by the output of `machine`

my @build_array = ();

my @build_kernel_array = (
    # Build kernel
    { name => "cd_confdir", command => 'chdir("/usr/src/sys/arch/amd64/conf")', perlcmd => 1},
    { name => "run_config", command => "/usr/sbin/config GENERIC" },
    { name => "cd_compiledir", command => 'chdir("/usr/src/sys/arch/amd64/compile/GENERIC")', perlcmd => 1 },
    { name => "run_makeclean", command => "make clean" },
    { name => "run_makedepend", command => "make depend" },
    { name => "run_make", command => "make" },
    { name => "run_makeinstall", command => "make install" },
    );

my @build_userland_array = (
    # Build userland
    { name => "clean_objdir", command => "rm -rf /usr/obj/*" },
    { name => "cd_usrsrc", command => 'chdir("/usr/src")', perlcmd =>1 },
    { name => "run_makeobj", command => "make obj" },
    { name => "cd_usrsrcetc", command => 'chdir("/usr/src/etc")', perlcmd =>1 },
    { name => "run_makedistribdirs", command => "env DESTDIR=/ make distrib-dirs" },
    { name => "cd_usrsrc", command => 'chdir("/usr/src")', perlcmd=>1 },
    { name => "run_makebuild", command => "make build" },
    );

sub run_command {
    # Update this to accept input of the array of commands. 
    # Check for shell or chdir or whatever? Eval if not a shell command?
    my %cmd_hash = %{$_[0]};
    my $cmd_name = $cmd_hash{'name'};
    my $cmd_path = $cmd_hash{'command'};
    my $cmd_perl = "";
    print "In run_command block. Name: $cmd_name, Command: $cmd_path\n";
    if (exists $cmd_hash{'perlcmd'}) {
	# Is this a Perl command we should eval?
	print "Running command as Perl: $cmd_path\n";
	eval($cmd_path) or die("problem running via eval"); # Eval(chdir()) doesn't return non-zero if failure.
    }
    else {
	print "Running command via system()\n";
	system($cmd_path);
    }
    my $raw_exit = $?;
    my $converted_exit = $raw_exit >> 8;
    if ($converted_exit != 0) {
	die("FATAL ERROR IN EXECUTION.\n Command: ${cmd_path}\nTIME TO DIE.\n");
	
    }
    #print "raw exit: $raw_exit, converted exit: $converted_exit\n";
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
        'updatesource' => \$options{'updatesource'},
        'kernel' => \$options{'build_kernel'},
        'userland' => \$options{'build_userland'},
        );

    if (defined($options{'updatesource'})) {
        print "Updating source CVS tree\n";
        &update_cvs;
    }
    else {
        print "Requested to skip updating OpenBSD source.\n";
    }

    # Add the kernel build commands to the build array
    if (defined($options{'build_kernel'})) {
        print "Building kernel\n";
        push @build_array, @build_kernel_array;
    }

    # Add the userland build commands to the build array
    if (defined($options{'build_userland'})) {
        print "Building userland\n";
        push @build_array, @build_userland_array;
    }

    # Iterate over the commands in @build_array
    for my $current (0 ... $#build_array) {
	&run_command($build_array[$current]);
    }
    
    print "Build complete.\n";
    exit 0;
};

&main;
