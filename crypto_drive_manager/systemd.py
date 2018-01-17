# Workaround for systemd incompatibility.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: January 17, 2018
# URL: https://github.com/xolox/python-crypto-drive-manager

"""Workaround for an incompatibility between `crypto-drive-manager` and system."""

# Standard library modules.
import glob
import os
import sys

# External dependencies.
import coloredlogs
from executor import execute, which
from verboselogs import VerboseLogger

CRYPTSETUP_GENERATOR = '/lib/systemd/system-generators/systemd-cryptsetup-generator'
"""
The absolute pathname of the ``systemd-cryptsetup-generator`` program (a
string). This is the location where systemd expects to find the program.
"""

CRYPTSETUP_GENERATOR_WRAPPED = '%s-original' % CRYPTSETUP_GENERATOR
"""
The absolute pathname of the moved ``systemd-cryptsetup-generator`` program (a
string). This is the location where crypto-drive-manager moves the original
program when installing the workaround.
"""

CRYPTSETUP_SERVICES = '/var/run/systemd/generator/systemd-cryptsetup@*.service'
"""A glob pattern that matches the generated ``*.service`` files (a string)."""

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def have_systemd_dependencies(mount_point):
    """
    Determine if any of the managed drives are affected by `systemd issue #3816`_.

    :param mount_point: The mount point for the virtual keys device (a string).
    :returns: :data:`True` if any of the encrypted drives managed by
              `crypto-drive-manager` are affected by `systemd issue #3816`_,
              :data:`False` if none of the managed drives are affected.

    If any of the encrypted drives managed by `crypto-drive-manager` are
    affected by `systemd issue #3816`_ then unmounting of the keys device will
    cause systemd to immediately unmount and lock those encrypted drives. When
    I first ran into this behavior it took me quite a lot of digging to figure
    out what exactly was going on and I was not amused :-P.

    Since then `crypto-drive-manager` has gained the ability to anticipate this
    issue and work around it by leaving the virtual keys device unlocked and
    mounted.

    Of course this goes straight against how `crypto-drive-manager` was
    originally designed and intended to work, but for now it will have
    to do because I don't know of a better workaround :-(.

    .. _systemd issue #3816: https://github.com/systemd/systemd/issues/3816
    """
    from crypto_drive_manager import find_managed_drives, match_prefix
    logger.verbose("Checking if we're affected by systemd issue #3816 ..")
    if execute('which', 'systemctl', check=False, silent=True):
        for device in find_managed_drives(mount_point):
            output = execute(
                'systemctl', 'show',
                'systemd-cryptsetup@%s.service' % device.target,
                capture=True, check=False, silent=True,
            )
            for line in output.splitlines():
                key, _, value = line.partition('=')
                if (key.strip() == 'RequiresMountsFor' and
                        match_prefix(value.strip(), mount_point)):
                    return True
    return False


def have_systemd_workaround():
    """
    Check if the workaround for `systemd issue #3816`_  is installed.

    :returns: :data:`True` if the workaround is installed, :data:`False` otherwise.
    """
    return os.path.islink(CRYPTSETUP_GENERATOR) and os.readlink(CRYPTSETUP_GENERATOR) == find_program_file()


def install_systemd_workaround():
    """Install the workaround for `systemd issue #3816`_ (if it isn't already installed)."""
    if have_systemd_workaround():
        logger.verbose("Workaround for systemd incompatibility is installed.")
    else:
        logger.info("Installing workaround for systemd incompatibility ..")
        program_file = find_program_file()
        if not os.path.isfile(CRYPTSETUP_GENERATOR_WRAPPED):
            logger.info("Moving original program out of place ..")
            os.rename(CRYPTSETUP_GENERATOR, CRYPTSETUP_GENERATOR_WRAPPED)
        os.symlink(program_file, CRYPTSETUP_GENERATOR)
        logger.info("Successfully installed workaround.")


def systemd_workaround_requested():
    """Check if execution of the systemd workaround has been requested."""
    try:
        return os.path.basename(sys.argv[0]) == os.path.basename(CRYPTSETUP_GENERATOR)
    except Exception:
        return False


def update_systemd_services():
    """Apply the workaround for `systemd issue #3816`_."""
    coloredlogs.install(syslog=True)
    logger.info("Running systemd-cryptsetup-generator program ..")
    execute(CRYPTSETUP_GENERATOR_WRAPPED, sudo=True)
    for service_file in glob.glob(CRYPTSETUP_SERVICES):
        # Read the *.service file.
        logger.info("Reading %s ..", service_file)
        with open(service_file) as handle:
            contents = list(handle)
        # Remove the 'RequiresMountsFor' field.
        modified = []
        for line in contents:
            key, _, value = line.partition('=')
            if key.strip() == 'RequiresMountsFor':
                logger.info("Stripping line: %s", line.strip())
            else:
                modified.append(line)
        # Check if a modification was made.
        if modified != contents:
            logger.info("Saving %s ..", service_file)
            # Save the modified *.service file.
            with open(service_file, 'w') as handle:
                for line in modified:
                    handle.write(line)


def find_program_file():
    """Find the absolute pathname of the `crypto-drive-manager` executable."""
    value = sys.argv[0]
    msg = "Failed to determine absolute pathname of program!"
    if not os.path.isabs(value):
        candidates = which(value)
        if not candidates:
            raise Exception(msg)
        value = candidates[0]
    if not os.access(value, os.X_OK):
        raise Exception(msg)
    return value
