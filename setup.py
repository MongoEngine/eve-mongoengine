#!/usr/bin/env python

from setuptools import setup

__version__ = "1.27.0"


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="Eve-Mongoengine2",
    version=__version__,
    url="https://github.com/wangsha/eve-mongoengine",
    author="Wang Sha",
    description="An Eve extension for Mongoengine ODM support",
    packages=["eve_mongoengine"],
    zip_safe=False,
    test_suite="tests",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    platforms="any",
    install_requires=["Eve", "Mongoengine", "blinker"],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">3",
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": ["*.md"],
    },
)
