# Command line interface for crypto-drive-manager.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: January 18, 2018
# URL: https://github.com/xolox/python-crypto-drive-manager

"""
Usage: crypto-drive-manager [OPTIONS] [NAME, ..]

Safely, quickly and conveniently unlock an unlimited number of LUKS encrypted
devices using a single pass phrase.

By default all entries in /etc/crypttab that reference a key file located under
the mount point of the encrypted disk with key files are unlocked (as needed).
To unlock a subset of the configured devices you can pass one or more NAME
arguments that match mapper name(s) configured in /etc/crypttab.

Supported options:

  -i, --image-file=PATH

    Set the pathname of the file that contains the encrypted disk image with
    key files (defaults to '/root/encryption-keys.img').

  -n, --mapper-name=NAME

    Set the mapper device name for the encrypted disk with key files so that
    the device for the drive with key files will be created as
    '/dev/mapper/NAME' (defaults to 'encryption-keys').

  -m, --mount-point=PATH

    Set the pathname of the mount point for the encrypted disk with key files
    (defaults to '/mnt/keys').

  --install-systemd-workaround

    Replace the systemd-cryptsetup-generator program with a wrapper that
    removes the 'RequiresMountsFor' option from the generated configuration
    files at /var/run/systemd/generator/*.service.

    Refer to the readme for more details about how this works.

  -v, --verbose

    Increase logging verbosity (can be repeated).

  -q, --quiet

    Decrease logging verbosity (can be repeated).

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import getopt
import logging
import os
import sys

# External dependencies.
import coloredlogs
from humanfriendly.terminal import usage, warning

# Modules included in our package.
from crypto_drive_manager import initialize_keys_device
from crypto_drive_manager.systemd import (
    install_systemd_workaround,
    systemd_workaround_requested,
    update_systemd_services,
)

# Initialize a logger for this module.
logger = logging.getLogger(__name__)


def main():
    """Command line interface for the ``crypto-drive-manager`` program."""
    # Initialize logging to the terminal and system log.
    coloredlogs.install(syslog=True)
    # Define command line option defaults.
    image_file = '/root/encryption-keys.img'
    mapper_name = 'encryption-keys'
    mount_point = '/mnt/keys'
    install_workaround = False
    # Parse the command line arguments.
    try:
        options, arguments = getopt.getopt(sys.argv[1:], 'i:n:m:vqh', [
            'image-file=', 'mapper-name=', 'mount-point=',
            'install-systemd-workaround',
            'verbose', 'quiet', 'help',
        ])
        for option, value in options:
            if option in ('-i', '--image-file'):
                image_file = value
            elif option in ('-n', '--mapper-name'):
                mapper_name = value
            elif option in ('-m', '--mount-point'):
                mount_point = value
            elif option == '--install-systemd-workaround':
                install_workaround = True
            elif option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-q', '--quiet'):
                coloredlogs.decrease_verbosity()
            elif option in ('-h', '--help'):
                usage(__doc__)
                return
            else:
                assert False, "Unhandled option!"
    except Exception as e:
        warning("Error: Failed to parse command line arguments! (%s)", e)
        sys.exit(1)
    # Make sure we're running as root (after parsing the command
    # line so that root isn't required to list the usage message).
    if os.getuid() != 0:
        warning("Error: Please run this command as root!")
        sys.exit(1)
    # Decide if the systemd workaround is being executed based on sys.argv[0].
    if systemd_workaround_requested():
        update_systemd_services()
        # In this case none of the other code should run.
        return
    # Check if the operator wants to install the systemd workaround.
    if install_workaround:
        install_systemd_workaround()
    # Initialize the keys device and use it to unlock the managed drives?
    # Only if we didn't just install the systemd workaround OR the operator
    # requested to unlock specific drives.
    if (not install_workaround) or arguments:
        try:
            initialize_keys_device(
                image_file=image_file,
                mapper_name=mapper_name,
                mount_point=mount_point,
                volumes=arguments,
            )
        except KeyboardInterrupt:
            logger.error("Interrupted by Control-C, terminating ..")
            sys.exit(1)
        except Exception:
            logger.exception("Terminating due to unexpected exception!")
            sys.exit(1)
