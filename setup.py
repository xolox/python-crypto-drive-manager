#!/usr/bin/env python

# Setup script for the `crypto-drive-manager' package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: February 21, 2015
# URL: https://github.com/xolox/python-crypto-drive-manager

import os
import re
import setuptools

# Find the directory where the source distribution was unpacked.
source_directory = os.path.dirname(os.path.abspath(__file__))

# Find the current version.
module = os.path.join(source_directory, 'crypto_drive_manager', '__init__.py')
for line in open(module, 'r'):
    match = re.match(r'^__version__\s*=\s*["\']([^"\']+)["\']$', line)
    if match:
        version_string = match.group(1)
        break
else:
    raise Exception("Failed to extract version from %s!" % module)

# Fill in the long description (for the benefit of PyPI)
# with the contents of README.rst (rendered by GitHub).
readme_file = os.path.join(source_directory, 'README.rst')
readme_text = open(readme_file).read()

# Fill in the installation requirements based on requirements.txt.
requirements_file = os.path.join(source_directory, 'requirements.txt')
requirements = list(filter(None, (re.sub('^\s*#.*|\s#.*', '', line).strip() for line in open(requirements_file))))

setuptools.setup(
    name='crypto-drive-manager',
    version=version_string,
    description="Unlock all your encrypted drives with one pass phrase.",
    long_description=readme_text,
    url='https://github.com/xolox/python-crypto-drive-manager',
    author='Peter Odding',
    author_email='peter@peterodding.com',
    packages=setuptools.find_packages(),
    entry_points=dict(console_scripts=['crypto-drive-manager = crypto_drive_manager.cli:main']),
    install_requires=requirements,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Security :: Cryptography',
        'Topic :: System :: Filesystems',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities'])
