# Command line interface for crypto-drive-manager.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: February 21, 2015
# URL: https://github.com/xolox/python-crypto-drive-manager

"""
Usage: crypto-drive-manager [OPTIONS]

Safely, quickly and conveniently unlock an unlimited number of LUKS encrypted
devices using a single pass phrase.

Supported options:

  -i, --image-file=PATH

    Set the pathname of the file that contains the encrypted disk image with
    key files (defaults to ``/root/encryption-keys.img``).

  -n, --mapper-name=NAME

    Set the mapper device name for the encrypted disk with key files so that
    the device for the drive with key files will be created as
    ``/dev/mapper/NAME`` (defaults to ``encryption-keys``).

  -m, --mount-point=PATH

    Set the pathname of the mount point for the encrypted disk with key files
    (defaults to /mnt/keys).

  -v, --verbose

    Make more noise (increase logging verbosity).

  -q, --quiet

    Make less noise (decrease logging verbosity).

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

# Modules included in our package.
from crypto_drive_manager import initialize_keys_device

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

def main():
    """Command line interface for the ``crypto-drive-manager`` program."""
    if os.getuid() != 0:
        print("Error: Please run this command as root!")
        sys.exit(1)
    # Initialize logging to the terminal.
    coloredlogs.install()
    # Parse the command line arguments.
    image_file = '/root/encryption-keys.img'
    mapper_name = 'encryption-keys'
    mount_point = '/mnt/keys'
    try:
        options, arguments = getopt.getopt(sys.argv[1:], 'i:n:m:vqh', [
            'image-file=', 'mapper-name=', 'mount-point=',
            'verbose', 'quiet', 'help'
        ])
        for option, value in options:
            if option in ('-i', '--image-file'):
                image_file = value
            elif option in ('-n', '--mapper-name'):
                mapper_name = value
            elif option in ('-m', '--mount-point'):
                mount_point = value
            elif option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-q', '--quiet'):
                coloredlogs.decrease_verbosity()
            elif option in ('-h', '--help'):
                usage()
                return
            else:
                assert False, "Unhandled option!"
    except Exception as e:
        print("Failed to parse command line arguments! (%s)" % e)
        print("")
        usage()
        sys.exit(1)
    try:
        # Initialize the keys device and use it to unlock all managed drives.
        initialize_keys_device(image_file=image_file,
                               mapper_name=mapper_name,
                               mount_point=mount_point)
    except KeyboardInterrupt:
        sys.stderr.write('\r')
        logger.error("Interrupted by Control-C, terminating ..")
        sys.exit(1)
    except Exception:
        logger.exception("Encountered an unhandled exception, terminating!")
        sys.exit(1)

def usage():
    """Print a friendly usage message to the terminal."""
    print(__doc__.strip())
