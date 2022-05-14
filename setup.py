# -*- coding: utf-8 -*-
"""
Spork
-----

A "little language" designed to facilitate the extraction and processing of
data held in XML or HTML files.

copyright © 2015-2022 Oracle Corporation
copyright © 2022 Sioned Arrowsmith
"""

from distutils.core import setup
setup(name='spork',
      version='0.2.1',
      description='The Spork little language',
      author='S Arrowsmith',
      author_email='sion.arrowsmith@gmail.com',
      url='https://github.com/sarrowsmith/spork',
      license='MIT',
      py_modules=['sporklib'],
      scripts=['spork'],
      package_data={'': ['README.md', 'LICENSE']},
      #install_requires=['lxml', 'cssselect', 'tinycss'],
      )
