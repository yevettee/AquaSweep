from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'aqua_detection'

setup(
    name='aqua_detection',  # Use underscore, not hyphen
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='woody',
    maintainer_email='woody.myung@gmail.com',
    description='AquaSweep Fish Detection Package - SAM2/YOLO + DINOv2 Pipeline',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'fish_detection_node = aqua_detection.fish_detection_node:main',
        ],
    },
)
