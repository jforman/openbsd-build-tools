#!/usr/bin/perl

@commands_array = (
    { name => "cd_confdir", path => "cd /usr/src/sys/arch/i386/conf" },
    { name => "run_config", path => "/usr/sbin/config GENERIC"},
    );

sub run_command {
    print "\n";
    $command_name = $_[0];
    $command_path = $_[1];
    print "name: $command_name\n";
    print "to run: $command_path\n";
};

sub main {
    if ($ARGV[0] eq "skipcvs") {
        print "Skip updating your OpenBSD source via CVS.\n";
    }
    else {
        if (-d "/usr/src") {
            print "Source checkout exists, updating files\n";
        }
        else {
            print "Source checkout does not exist. Checking out from CVS repo.\n";
        }
    }

    # for $current ( 0 ... $#commands_array) {
    #     &run_command($commands_array[$current]{name}, $commands_array[$current]{path});
    #     print "command output: $command_output\n";
};

&main;
