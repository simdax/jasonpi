#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

setup(
    name='jasonpi',
    version='0.4.0',
    description='Authentication package to use with '
                'django-rest-framework & json-api',
    url='http://github.com/gobadiah/jasonpi',
    author='Michaël Journo',
    author_email='gobadiah@gmail.com',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pyjwt',
        'httplib2',
        'oauth2client',
        'google-api-python-client',
        'facebook-sdk',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    zip_safe=True,
)
