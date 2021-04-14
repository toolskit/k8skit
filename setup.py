import sys
import os
from setuptools import setup, find_packages, Extension

setup (
      name = 'k8skit',
      version = '1.0',
      author = 'moonhak',
      author_email = 'moonhak@**.com',
      maintainer = 'moonhak',
      maintainer_email = 'moonhak@**.com',
      description = "k8skit",
      packages = ['k8skit'],
      package_dir = {'k8skit' : ''},
)

