from setuptools import find_packages
from setuptools import setup

setup(
    name='aqua_interfaces',
    version='0.0.0',
    packages=find_packages(
        include=('aqua_interfaces', 'aqua_interfaces.*')),
)
