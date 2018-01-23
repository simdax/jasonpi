#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='jasonpi',
      version='0.1',
      description='Authentication package to use with '
                  'django-rest-framework & json-api',
      url='http://github.com/gobadiah/jasonpi',
      author='Michaël Journo',
      author_email='gobadiah@gmail.com',
      license='MIT',
      packages=['jasonpi'],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      zip_safe=True)
