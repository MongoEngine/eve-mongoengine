#!/usr/bin/env python

from setuptools import setup

from eve_mongoengine import get_version

setup(
    name="Eve-Mongoengine",
    version=get_version(),
    url="https://github.com/wangsha/eve-mongoengine",
    author="Wang Sha",
    description="An Eve extension for Mongoengine ODM support",
    packages=["eve_mongoengine"],
    zip_safe=False,
    test_suite="tests",
    include_package_data=True,
    platforms="any",
    install_requires=["Eve", "Mongoengine", "Blinker"],
)
