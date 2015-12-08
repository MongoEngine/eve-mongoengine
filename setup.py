#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='Eve-Mongoengine',
    version='0.0.9.4',
    url='https://github.com/hellerstanislav/eve-mongoengine',
    author='Stanislav Heller',
    author_email='heller.stanislav@gmail.com',
    description='An Eve extension for Mongoengine ODM support',
    packages=['eve_mongoengine'],
    zip_safe=False,
    test_suite="tests",
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Eve>=0.5.3',
        'Mongoengine>=0.8.7',
        'Blinker'
    ]
)
