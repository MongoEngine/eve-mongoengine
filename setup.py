#!/usr/bin/env python

from setuptools import setup

__version__ = "1.3.0"


LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.md').read()
except:
    pass

setup(
    name="Eve-Mongoengine2",
    version=__version__,
    url="https://github.com/wangsha/eve-mongoengine",
    author="Wang Sha",
    description="An Eve extension for Mongoengine ODM support",
    packages=["eve_mongoengine"],
    zip_safe=False,
    test_suite="tests",
    long_description=LONG_DESCRIPTION,
    include_package_data=True,
    platforms="any",
    install_requires=["Eve", "Mongoengine", "blinker"],
)
