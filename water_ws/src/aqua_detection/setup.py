from setuptools import find_packages, setup

package_name = 'aqua_detection'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rokey',
    maintainer_email='sujinchoi17@gmail.com',
    description='AquaSweep Camera Object Detection package',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'top_detection_node = aqua_detection.top.detection_node:main',
        ],
    },
)
