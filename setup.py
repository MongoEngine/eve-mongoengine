#!/usr/bin/env python

from setuptools import setup

setup(
    name="Eve-Mongoengine",
    version="0.1",
    url="https://github.com/wangsha/eve-mongoengine",
    author="Stanislav Heller",
    author_email="heller.stanislav@gmail.com",
    description="An Eve extension for Mongoengine ODM support",
    packages=["eve_mongoengine"],
    zip_safe=False,
    test_suite="tests",
    include_package_data=True,
    platforms="any",
    install_requires=["Eve", "Mongoengine", "Blinker"],
)
