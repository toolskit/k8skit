import sys
import os
from setuptools import setup, find_packages, Extension

setup (
      name = 'k8skit',
      version = '1.0',
      author = 'moonhak',
      author_email = 'moonhak@91act.com',
      maintainer = 'moonhak',
      maintainer_email = 'moonhak@91act.com',
      description = "k8skit",
      packages = ['k8skit'],
      package_dir = {'k8skit' : ''},
)

