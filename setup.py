#!/usr/bin/env python

# Setup script for the `crypto-drive-manager' package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: January 5, 2018
# URL: https://github.com/xolox/python-crypto-drive-manager

"""
Setup script for the `crypto-drive-manager` package.

**python setup.py install**
  Install from the working directory into the current Python environment.

**python setup.py sdist**
  Build a source distribution archive.

**python setup.py bdist_wheel**
  Build a wheel distribution archive.
"""

# Standard library modules.
import codecs
import os
import re
import sys

# De-facto standard solution for Python packaging.
from setuptools import find_packages, setup


def get_contents(*args):
    """Get the contents of a file relative to the source distribution directory."""
    with codecs.open(get_absolute_path(*args), 'r', 'UTF-8') as handle:
        return handle.read()


def get_version(*args):
    """Extract the version number from a Python module."""
    contents = get_contents(*args)
    metadata = dict(re.findall('__([a-z]+)__ = [\'"]([^\'"]+)', contents))
    return metadata['version']


def get_install_requires():
    """Get the conditional dependencies for source distributions."""
    install_requires = get_requirements('requirements.txt')
    if 'bdist_wheel' not in sys.argv:
        if sys.version_info[:2] < (3, 4):
            install_requires.append('enum34 >= 1.1.6')
    return sorted(install_requires)


def get_extras_require():
    """Get the conditional dependencies for wheel distributions."""
    extras_require = {}
    if have_environment_marker_support():
        expression = ':%s' % ' or '.join([
            'python_version == "2.6"',
            'python_version == "2.7"',
            'python_version == "3.0"',
            'python_version == "3.1"',
            'python_version == "3.2"',
            'python_version == "3.3"',
        ])
        extras_require[expression] = ['enum34 >= 1.1.6']
    return extras_require


def get_requirements(*args):
    """Get requirements from pip requirement files."""
    requirements = set()
    with open(get_absolute_path(*args)) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub(r'^#.*|\s#.*', '', line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r'\s+', '', line))
    return sorted(requirements)


def get_absolute_path(*args):
    """Transform relative pathnames into absolute pathnames."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)


def have_environment_marker_support():
    """
    Check whether setuptools has support for PEP-426 environment marker support.

    Based on the ``setup.py`` script of the ``pytest`` package:
    https://bitbucket.org/pytest-dev/pytest/src/default/setup.py
    """
    try:
        from pkg_resources import parse_version
        from setuptools import __version__
        return parse_version(__version__) >= parse_version('0.7.2')
    except Exception:
        return False


setup(name='crypto-drive-manager',
      version=get_version('crypto_drive_manager', '__init__.py'),
      description="Unlock all your encrypted drives with one pass phrase.",
      long_description=get_contents('README.rst'),
      url='https://github.com/xolox/python-crypto-drive-manager',
      author="Peter Odding",
      author_email='peter@peterodding.com',
      packages=find_packages(),
      install_requires=get_install_requires(),
      extras_require=get_extras_require(),
      entry_points=dict(console_scripts=[
          'crypto-drive-manager = crypto_drive_manager.cli:main',
      ]),
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'Intended Audience :: Information Technology',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Topic :: Security :: Cryptography',
          'Topic :: System :: Filesystems',
          'Topic :: System :: Systems Administration',
          'Topic :: Terminals',
          'Topic :: Utilities',
      ])
