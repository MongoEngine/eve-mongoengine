#!/usr/bin/env python

from setuptools import setup

__version__ = "1.3.0"

setup(
    name="Eve-Mongoengine2",
    version=__version__,
    url="https://github.com/wangsha/eve-mongoengine",
    author="Wang Sha",
    description="An Eve extension for Mongoengine ODM support",
    packages=["eve_mongoengine"],
    zip_safe=False,
    test_suite="tests",
    include_package_data=True,
    platforms="any",
    install_requires=["Eve", "Mongoengine", "blinker"],
)
