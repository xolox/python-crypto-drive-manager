crypto-drive-manager: Unlock all your encrypted drives with one pass phrase
---------------------------------------------------------------------------

The ``crypto-drive-manager`` program allows you to safely, quickly and
conveniently unlock an unlimited number of `LUKS encrypted devices`_ using a
single pass phrase. You can think of it as a `key pass`_ for LUKS encrypted
devices. It works by creating a small (10 MB) encrypted file system inside a
regular file (using a `loop device`_) and storing key files for the encrypted
devices of your choosing inside this encrypted file system. Each time you run
the program it temporarily unlocks the 10 MB encrypted file system and uses the
key files to unlock and mount encrypted devices that are present and not
already unlocked.

.. contents::
   :local:

Installation
------------

The `crypto-drive-manager` program is written in Python and is available on
PyPI_ which means installation should be as simple as::

  $ pip install crypto-drive-manager

There's actually a multitude of ways to install Python packages (e.g. the `per
user site-packages directory`_, `virtual environments`_ or just installing
system wide) and I have no intention of getting into that discussion here, so
if this intimidates you then read up on your options before returning to these
instructions ;-).

Configuration
-------------

The `crypto-drive-manager` program doesn't have a configuration file because
it looks at your system configuration to infer what it should do. You need to
create or change ``/etc/crypttab`` in order to enable `crypto-drive-manager`.
As an example here's my ``/etc/crypttab`` file::

  # <target name>  <source device>                            <key file>                 <options>
  internal-hdd     UUID=626f4560-cf80-4ed9-b211-ac263b41ca67  none                       luks
  media-files      UUID=6d413429-f8d1-4d8e-8a3a-075603b8efdd  /mnt/keys/media-files.key  luks,noauto
  mirror3          UUID=978d7a3a-c902-43e6-aa71-5654d406c247  /mnt/keys/mirror3.key      luks,noauto
  mirror4          UUID=7a48e547-1dfa-4c6a-96e9-05842c87465d  /mnt/keys/mirror4.key      luks,noauto
  mirror5          UUID=ac6aa22a-0c32-4bd9-829a-75316177affb  /mnt/keys/mirror5.key      luks,noauto
  mirror6          UUID=00474636-6d6e-4ecc-a7d6-21b42d850ac6  /mnt/keys/mirror6.key      luks,noauto
  mirror7          UUID=ec56dc10-1086-4f2b-808c-88995cb8b513  /mnt/keys/mirror7.key      luks,noauto

You can see why I don't want to manage all of these encrypted devices manually
by entering pass phrases for each of them :-). Even though my root device
(``internal-hdd``) is also encrypted, storing key files to unlock my encrypted
devices on my root device doesn't feel right because the key files will be
exposed at all times.

You tell `crypto-drive-manager` to manage an encrypted device by setting the
key file (the third field in ``/etc/crypttab``) to a file located under the
mount point used by `crypto-drive-manager` ( ``/mnt/keys`` by default). Every
time you run `crypto-drive-manager` it parses ``/etc/crypttab`` to find and
unlock managed devices. The ``UUID=...`` definition in ``/etc/crypttab`` is
used to check if the physical device exists in ``/dev/disk/by-uuid``. Because
of this a source device definition with a ``UUID=...`` value is required.

Each physical device that exists is initialized, unlocked and mounted. Device
initialization happens when the key file for the encrypted device doesn't exist
yet: The key file is created with 4 KB of random bytes and installed as a key
on the encrypted device.

The end result is a program that requires a single pass phrase to unlock a
virtual keys device containing key files used to unlock a group of encrypted
devices. Once the encrypted devices have been unlocked the virtual keys device
is unmounted and the keys are no longer available (except in memory, which
cannot be avoided to the best of my knowledge).

Usage
-----

.. A DRY solution to avoid duplication of the `crypto-drive-manager --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('crypto_drive_manager.cli')
.. ]]]

**Usage:** `crypto-drive-manager [OPTIONS] [NAME, ..]`

Safely, quickly and conveniently unlock an unlimited number of LUKS encrypted
devices using a single pass phrase.

By default all entries in /etc/crypttab that reference a key file located under
the mount point of the encrypted disk with key files are unlocked (as needed).

To unlock a subset of the configured devices you can pass one or more ``NAME``
arguments that match the mapper name(s) configured in /etc/crypttab.

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-i``, ``--image-file=PATH``","Set the pathname of the file that contains the encrypted disk image with
   key files (defaults to '/root/encryption-keys.img')."
   "``-n``, ``--mapper-name=NAME``","Set the mapper device name for the encrypted disk with key files so that
   the device for the drive with key files will be created as
   '/dev/mapper/NAME' (defaults to 'encryption-keys')."
   "``-m``, ``--mount-point=PATH``","Set the pathname of the mount point for the encrypted disk with key files
   (defaults to '/mnt/keys')."
   "``-v``, ``--verbose``",Increase logging verbosity (can be repeated).
   "``-q``, ``--quiet``",Decrease logging verbosity (can be repeated).
   "``-h``, ``--help``",Show this message and exit.

.. [[[end]]]

Contact
-------

The latest version of `crypto-drive-manager` is available on PyPI_ and
GitHub_. For bug reports please create an issue on GitHub_. If you have
questions, suggestions, etc. feel free to send me an e-mail at
`peter@peterodding.com`_.

License
-------

This software is licensed under the `MIT license`_.

© 2017 Peter Odding.

.. External references:
.. _GitHub: https://github.com/xolox/python-crypto-drive-manager
.. _key pass: http://en.wikipedia.org/wiki/Password_manager
.. _loop device: http://en.wikipedia.org/wiki/Loop_device
.. _LUKS encrypted devices: http://en.wikipedia.org/wiki/Linux_Unified_Key_Setup
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _per user site-packages directory: https://www.python.org/dev/peps/pep-0370/
.. _peter@peterodding.com: mailto:peter@peterodding.com
.. _PyPI: https://pypi.python.org/pypi/crypto-drive-manager
.. _virtual environments: http://docs.python-guide.org/en/latest/dev/virtualenvs/
