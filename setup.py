import os
import re
import subprocess
from setuptools import setup, find_packages  # type: ignore
from pathlib import Path

with open('README.md') as f:
    long_description = f.read()

version_re = re.compile('^Version: (.+)$', re.M)
package_name = 'django-database-routing'


def get_version():
    """
    Reads version from git status or PKG-INFO

    https://gist.github.com/pwithnall/7bc5f320b3bdf418265a
    """
    d: Path = Path(__file__).absolute().parent
    git_dir = d.joinpath('.git')
    if git_dir.is_dir():
        # Get the version using "git describe".
        cmd = 'git describe --tags --match [0-9]*'.split()
        try:
            version = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            return None

        # PEP 386 compatibility
        if '-' in version:
            version = '.post'.join(version.split('-')[:2])

        # Don't declare a version "dirty" merely because a time stamp has
        # changed. If it is dirty, append a ".dev1" suffix to indicate a
        # development revision after the release.
        with open(os.devnull, 'w') as fd_devnull:
            subprocess.call(['git', 'status'],
                            stdout=fd_devnull, stderr=fd_devnull)

        cmd = 'git diff-index --name-only HEAD'.split()
        try:
            dirty = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            return None

        if dirty != '':
            version += '.dev1'
    else:
        # Extract the version from the PKG-INFO file.
        try:
            with open('PKG-INFO') as v:
                version = version_re.search(v.read()).group(1)
        except FileNotFoundError:
            version = None

    return version


setup(
    name=package_name,
    version=get_version() or 'dev',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=['database_routing'],
    install_requres=[
        'Django'
    ],
    url='https://github.com/just-work/django-database-routing',
    license='Apache License v2.0',
    author='tumbler',
    author_email='zimbler@gmail.com',
    description='''Provides primary-replica routing
        and force primary context manager for Django'''

)
