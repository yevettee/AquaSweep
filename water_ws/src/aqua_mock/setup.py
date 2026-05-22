from setuptools import find_packages, setup

package_name = 'aqua_mock'

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
    maintainer='woody',
    maintainer_email='woody.myung@gmail.com',
    description='Mock publishers for AquaSweep dashboard/planner testing',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'mock_publisher_node = aqua_mock.mock_publisher_node:main',
        ],
    },
)
