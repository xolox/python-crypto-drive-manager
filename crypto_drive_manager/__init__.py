# Python API for crypto-drive-manager.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: February 21, 2015
# URL: https://github.com/xolox/python-crypto-drive-manager

__version__ = '1.0'

# Standard library modules.
import functools
import logging
import os
import re

# External dependencies.
from executor import execute
from humanfriendly import pluralize, Timer

# Initialize a logger for this module.
logger = logging.getLogger(__name__)
execute = functools.partial(execute, logger=logger)

def initialize_keys_device(image_file, mapper_name, mount_point):
    """
    Initialize and activate the virtual keys device and use it to activate encrypted volumes.

    :param image_file: The absolute pathname of the image file for the virtual
                       keys device (a string). If you are using an encrypted
                       root drive this file should reside on the ``/boot``
                       partition to avoid chicken and egg problems :-).
    :param mapper_name: The device mapper name for the virtual keys device (a
                        string).
    :param mount_point: The mount point for the virtual keys device (a string).
    """
    first_run = not os.path.isfile(image_file)
    initialized = not first_run
    mapper_device = '/dev/mapper/%s' % mapper_name
    try:
        # Create the virtual keys device (on the first run).
        if first_run:
            logger.info("Creating virtual keys device %s ..", image_file)
            execute('dd', 'if=/dev/zero', 'of=%s' % image_file, 'bs=%i' % (1024 * 1024), 'count=10')
            execute('cryptsetup', 'luksFormat', image_file)
        # Unlock the keys device.
        if not os.path.exists(mapper_device):
            logger.info("Unlocking virtual keys device %s ..", image_file)
            execute('cryptsetup', 'luksOpen', image_file, mapper_name)
        unlocked_timer = Timer()
        with finalizer('cryptsetup', 'luksClose', mapper_name):
            # Create a file system on the virtual keys device (on the first run).
            if first_run:
                logger.info("Creating file system on virtual keys device ..")
                execute('mkfs.ext4', mapper_device)
                initialized = True
            # Mount the virtual keys device.
            logger.info("Mounting virtual keys device ..")
            if not os.path.isdir(mount_point):
                os.makedirs(mount_point)
            if not os.path.ismount(mount_point):
                execute('mount', mapper_device, mount_point)
            with finalizer('umount', mount_point):
                os.chmod(mount_point, 0o700)
                # Create, install and use the keys to unlock the drives.
                num_unlocked = 0
                for device in find_managed_drives(mount_point):
                    if device['available'] and activate_encrypted_drive(
                            mapper_name=device['name'],
                            physical_device=device['physical_device'],
                            keys_directory=mount_point,
                            reset=first_run):
                        num_unlocked += 1
                logger.info("Unlocked %s.", pluralize(num_unlocked, "encrypted device"))
        logger.debug("Virtual keys device was accessible for %s.", unlocked_timer)
    finally:
        if not initialized:
            logger.warning("Initialization procedure was interrupted, deleting %s ..", image_file)
            if os.path.isfile(image_file):
                os.unlink(image_file)

def activate_encrypted_drive(mapper_name, physical_device, keys_directory, reset=False):
    """
    Initialize and activate an encrypted volume.

    :param mapper_name: The device mapper name for the virtual keys device (a
                        string).
    :param physical_device: The pathname of the physical drive that contains
                            the encrypted LUKS volume (a string).
    :param keys_directory: The mount point for the virtual keys device (a
                           string).
    :param reset: If ``True`` the key file for the encrypted volume will be
                  regenerated (overwriting any previous key).
    """
    mapper_device = '/dev/mapper/%s' % mapper_name
    device_exists = os.path.exists(mapper_device)
    if reset or not device_exists:
        key_file = os.path.join(keys_directory, '%s.key' % mapper_name)
        if reset or not os.path.isfile(key_file):
            logger.info("Creating %s to unlock %s (%s)", key_file, mapper_name, physical_device)
            execute('dd', 'if=/dev/urandom', 'of=%s' % key_file, 'bs=4', 'count=1024')
            logger.info("Installing %s on %s ..", key_file, physical_device)
            execute('cryptsetup', 'luksAddKey', physical_device, key_file)
        os.chmod(key_file, 0o400)
        if not device_exists:
            logger.info("Unlocking encrypted drive %s ..", mapper_name)
            if not execute('cryptdisks_start', mapper_name, check=False):
                logger.warning("Failed to unlock encrypted drive %s!", mapper_name)
                return False
    if drive_needs_mounting(mapper_device):
        logger.info("Mounting %s ..", mapper_device)
        if not execute('mount', mapper_device, check=False):
            logger.warning("Failed to mount %s!", mapper_device)
            return False
    return True

def find_managed_drives(keys_directory):
    """
    Find the encrypted drives that ``crypto-drive-manager`` manages.

    :param keys_directory: The mount point for the virtual keys device (a
                           string).
    :returns: A generator of dictionaries with the following device properties:

              - ``name``: The device mapper name (a string).
              - ``key_file``: The pathname of the key file (a string or
                              ``None``).
              - ``options``: A :py:class:`set` of options (strings).
              - ``available``: ``True`` if the physical drive is available,
                               ``False`` otherwise.
              - ``physical_device``: The pathname of the physical drive (this
                                     key/value pair is only available if
                                     ``available=True``).
    """
    for tokens in parse_tab_file('/etc/crypttab'):
        if len(tokens) == 4:
            mapper_name, location, key_file, options = tokens
            common_prefix = os.path.commonprefix([keys_directory, key_file])
            tokenized_options = set(filter(None, options.split(',')))
            if 'luks' in tokenized_options and common_prefix == keys_directory:
                properties = dict(name=mapper_name,
                                  key_file=key_file if key_file != 'none' else None,
                                  options=tokenized_options,
                                  available=False)
                # Find the physical device.
                name, _, value = location.partition('=')
                if name.upper() == 'UUID':
                    disk_by_uuid = '/dev/disk/by-uuid/%s' % value.lower()
                    if os.path.exists(disk_by_uuid):
                        properties['available'] = True
                        properties['physical_device'] = os.path.realpath(disk_by_uuid)
                yield properties

def drive_needs_mounting(mapper_device):
    """
    Check if an encrypted drive can be mounted directly.

    :param mapper_device: The pathname of the device mapper device (a string).
    :returns: ``True`` if the drive should be mounted, ``False`` otherwise.
    """
    if mapper_device in find_mounted_devices():
        logger.debug("Drive %s is already mounted.", mapper_device)
        return False
    for line in execute('blkid', '-o', 'export', mapper_device, capture=True).splitlines():
        name, _, value = line.partition('=')
        if name.lower() == 'type' and value.lower() == 'lvm2_member':
            logger.debug("Drive %s is part of an LVM volume group so we won't try to mount it.", mapper_device)
            return False
    logger.debug("Drive %s not yet mounted.", mapper_device)
    return True

def find_mounted_devices():
    """
    Find the mounted devices.

    :returns: A generator of device pathnames (strings).
    """
    for tokens in parse_tab_file('/etc/mtab'):
        yield tokens[0]

def parse_tab_file(pathname):
    """
    Parse UNIX configuration files like ``/etc/fstab`` and ``/etc/crypttab``.

    Automatically strips comments and tokenizes input by splitting on whitespace.

    :param pathname: The absolute pathname of the configuration file (a
                     string).
    :returns: A generator of lists with tokenized lines.
    """
    with open(pathname) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub('#.*', '', line)
            # Tokenize input.
            tokens = line.split()
            if tokens:
                yield tokens

class finalizer(object):

    """
    Context manager that unconditionally runs an external command when the
    :py:keyword:`with` statement ends.
    """

    def __init__(self, *args, **kw):
        """
        Initialize the context manager.

        :param args: The positional argument(s) for py:func:`execute()`.
        :param kw: Any keyword arguments for py:func:`execute()`.
        """
        self.args = args
        self.kw = kw

    def __enter__(self):
        pass

    def __exit__(self, *args):
        """Unconditionally run the previously specified external command."""
        execute(*self.args, **self.kw)
