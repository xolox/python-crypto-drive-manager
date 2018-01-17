# Python API for crypto-drive-manager.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: January 18, 2018
# URL: https://github.com/xolox/python-crypto-drive-manager

"""Python API for `crypto-drive-manager`."""

# Standard library modules.
import enum
import os

# External dependencies.
from executor import execute
from humanfriendly import Timer, compact, concatenate, pluralize
from linux_utils.crypttab import parse_crypttab
from linux_utils.fstab import find_mounted_filesystems
from linux_utils.luks import cryptdisks_start
from verboselogs import VerboseLogger

# Modules included in our package.
from crypto_drive_manager.systemd import have_systemd_dependencies

__version__ = '3.0'
"""Semi-standard module versioning."""

# Initialize a logger for this module.
logger = VerboseLogger(__name__)


def initialize_keys_device(image_file, mapper_name, mount_point, volumes=(), cleanup=None):
    """
    Initialize and activate the virtual keys device and use it to activate encrypted volumes.

    :param image_file: The absolute pathname of the image file for the virtual
                       keys device (a string). If you are using an encrypted
                       root drive this file should reside on the ``/boot``
                       partition to avoid chicken and egg problems :-).
    :param mapper_name: The device mapper name for the virtual keys device (a
                        string).
    :param mount_point: The mount point for the virtual keys device (a string).
    :param volumes: An iterable of strings that match match mapper names
                    configured in /etc/crypttab. If given then only these
                    volumes will be unlocked. By default it's empty which means
                    all of the configured and available drives are unlocked.
    :param cleanup: :data:`True` to unmount and lock the virtual keys device
                    after use, :data:`False` to leave the device mounted or
                    :data:`None` to automatically figure out what the best
                    choice is (this is the default). See also
                    :func:`.have_systemd_dependencies()`.
    """
    first_run = not os.path.isfile(image_file)
    initialized = not first_run
    mapper_device = '/dev/mapper/%s' % mapper_name
    if cleanup is None:
        # Figure out whether it's safe to unmount and lock
        # the virtual keys device after we're done.
        if have_systemd_dependencies(mount_point):
            logger.notice(compact("""
                The virtual keys device will remain unlocked because
                you're running systemd and you appear to be affected
                by https://github.com/systemd/systemd/issues/3816.
            """))
            cleanup = False
        else:
            logger.verbose(compact("""
                Locking virtual keys device after use (this should be
                safe to do because it appears that you're not affected
                by https://github.com/systemd/systemd/issues/3816).
            """))
            cleanup = True
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
        with finalizer('cryptsetup', 'luksClose', mapper_name, enabled=cleanup):
            # Create a file system on the virtual keys device (on the first run).
            if first_run:
                logger.info("Creating file system on virtual keys device ..")
                execute('mkfs.ext4', mapper_device)
                initialized = True
            # Mount the virtual keys device.
            if not os.path.isdir(mount_point):
                os.makedirs(mount_point)
            if os.path.ismount(mount_point):
                logger.info("The virtual keys device is already mounted ..")
            else:
                logger.info("Mounting the virtual keys device ..")
                execute('mount', mapper_device, mount_point)
            with finalizer('umount', mount_point, enabled=cleanup):
                os.chmod(mount_point, 0o700)
                if volumes:
                    logger.verbose("Unlocking encrypted devices matching filter: %s", concatenate(map(repr, volumes)))
                else:
                    logger.verbose("Unlocking all configured and available encrypted devices ..")
                # Create, install and use the keys to unlock the drives.
                num_configured = 0
                num_available = 0
                num_unlocked = 0
                for device in find_managed_drives(mount_point):
                    if volumes and device.target not in volumes:
                        logger.verbose("Ignoring %s because it doesn't match the filter.", device.target)
                    elif device.is_available:
                        status = activate_encrypted_drive(
                            mapper_name=device.target,
                            physical_device=device.source_device,
                            keys_directory=mount_point,
                            reset=first_run,
                        )
                        if status & DriveStatus.UNLOCKED:
                            num_unlocked += 1
                        num_available += 1
                    num_configured += 1
                if num_unlocked > 0:
                    logger.success("Unlocked %s.", pluralize(num_unlocked, "encrypted device"))
                elif num_available > 0:
                    logger.info("Nothing to do! (%s already unlocked)", pluralize(num_available, "encrypted device"))
                elif num_configured > 0:
                    logger.info("Nothing to do! (no encrypted devices available)")
                else:
                    logger.info("Nothing to do! (no encrypted drives configured)")
        if cleanup:
            logger.verbose("Virtual keys device was accessible for %s.", unlocked_timer)
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
    :return: An integer created by combining members of the
             :class:`DriveStatus` enumeration using bitwise or.
    :raises: :exc:`~executor.ExternalCommandFailed` when a program
             like ``cryptsetup`` or ``mount`` reports an error.
    """
    status = DriveStatus.DEFAULT
    mapper_device = '/dev/mapper/%s' % mapper_name
    device_exists = os.path.exists(mapper_device)
    if reset or not device_exists:
        key_file = os.path.join(keys_directory, '%s.key' % mapper_name)
        if reset or not os.path.isfile(key_file):
            logger.info("Creating %s to unlock %s (%s)", key_file, mapper_name, physical_device)
            execute('dd', 'if=/dev/urandom', 'of=%s' % key_file, 'bs=4', 'count=1024')
            logger.info("Installing %s on %s ..", key_file, physical_device)
            execute('cryptsetup', 'luksAddKey', physical_device, key_file)
            status |= DriveStatus.INITIALIZED
        os.chmod(key_file, 0o400)
        if not device_exists:
            logger.info("Unlocking encrypted drive %s ..", mapper_name)
            cryptdisks_start(mapper_name)
            status |= DriveStatus.UNLOCKED
    if drive_needs_mounting(mapper_device):
        logger.info("Mounting %s ..", mapper_device)
        execute('mount', mapper_device)
        status |= DriveStatus.MOUNTED
    return status


def find_managed_drives(keys_directory):
    """
    Find the encrypted drives managed by `crypto-drive-manager`.

    :param keys_directory: The mount point for the virtual keys device (a string).
    :returns: A generator of :class:`~linux_utils.crypttab.EncryptedFileSystemEntry` objects.
    """
    for entry in parse_crypttab():
        if ('luks' in entry.options and entry.key_file and
                match_prefix(entry.key_file, keys_directory)):
            yield entry


def match_prefix(pathname, prefix):
    """
    Check if a pathname has the expected prefix.

    :param pathname: The pathname of a file or directory (a string).
    :param prefix: The pathname of a directory expected to contain
                   the given `pathname` (a string).
    :returns: :data:`True` if `pathname` starts with `prefix`,
              :data:`False` otherwise.
    """
    # Normalize the input values to enable string comparison.
    pathname = os.path.normpath(pathname)
    prefix = os.path.normpath(prefix)
    # Make sure the prefix ends in a slash so that we take the boundaries
    # between path segments into account in the string comparison below.
    if not prefix.endswith(os.path.sep):
        prefix += os.path.sep
    # String comparison should work now? (famous last words)
    return pathname.startswith(prefix)


def drive_needs_mounting(mapper_device):
    """
    Check if an encrypted drive can be mounted directly.

    :param mapper_device: The pathname of the device mapper device (a string).
    :returns: ``True`` if the drive should be mounted, ``False`` otherwise.
    """
    if any(fs.device_file == mapper_device for fs in find_mounted_filesystems()):
        logger.verbose("Drive %s is already mounted.", mapper_device)
        return False
    for line in execute('blkid', '-o', 'export', mapper_device, capture=True).splitlines():
        name, _, value = line.partition('=')
        if name.lower() == 'type' and value.lower() == 'lvm2_member':
            logger.verbose("Drive %s is part of an LVM volume group so we won't try to mount it.", mapper_device)
            return False
    logger.verbose("Drive %s not yet mounted.", mapper_device)
    return True


class finalizer(object):

    """Context manager to run a command when the :keyword:`with` statement ends."""

    def __init__(self, *args, **kw):
        """
        Initialize the context manager.

        :param args: The positional argument(s) for py:func:`execute()`.
        :param kw: Any keyword arguments for py:func:`execute()`.
        """
        self.args = args
        self.enabled = kw.pop('enabled', True)
        self.kw = kw

    def __enter__(self):
        """Enable use as a context manager."""

    def __exit__(self, *args):
        """Unconditionally run the previously specified external command."""
        if self.enabled:
            execute(*self.args, **self.kw)


class DriveStatus(enum.IntEnum):

    """
    Enumeration for the actions taken by :func:`activate_encrypted_drive()`.

    The values of this enumeration are intended to be combined using bitwise
    operators exactly like how enum.Flag_ works since Python 3.6. To remain
    compatible with older Python versions `crypto-drive-manager` depends on
    the enum34_ package, which doesn't implement enum.Flag_. This explains
    why enum.Enum_ is used instead.

    .. _enum.Enum: https://docs.python.org/3/library/enum.html#creating-an-enum
    .. _enum.Flag: https://docs.python.org/3/library/enum.html#flag
    .. _enum34: https://pypi.python.org/pypi/enum34
    """

    DEFAULT = 0
    """The default, empty status (nothing was done)."""

    INITIALIZED = 1
    """A key file was generated and the key was installed on the encrypted drive."""

    UNLOCKED = 2
    """The encrypted drive was unlocked as configured in ``/etc/crypttab``."""

    MOUNTED = 4
    """The encrypted drive was mounted as configured in ``/etc/fstab``."""
