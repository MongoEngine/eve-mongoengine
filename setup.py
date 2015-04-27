#!/usr/bin/env python

from setuptools import setup, find_packages

LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

# Version Information
# (Using 'execfile' is not version safe)
exec(open('eve_mongoengine/__version__.py').read())
VERSION = get_version()

extra_opts = dict()

# Project Setup
setup(
    name='eve-mongoengine',
    version=VERSION,
    url='https://github.com/seglberg/eve-mongoengine',
    author='Stanislav Heller',
    author_email='heller.stanislav@{nospam}gmail.com',
    maintainer="Matthew Ellison",
    maintainer_email="seglberg@gmail.com",
    description='An Eve extension for Mongoengine ODM support',
    long_description=LONG_DESCRIPTION,
    platforms=['any'],
    packages=find_packages(exclude=["test*"]),
    test_suite="tests",
    license='MIT',
    include_package_data=True,
    install_requires=[
        'Eve>=0.5.3',
        'Blinker',
        'Mongoengine>=0.8.7,<=0.9',
    ],
    **extra_opts
)
