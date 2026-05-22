from setuptools import find_packages, setup

package_name = 'aqua_controller'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/all_robots.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='AquaSweep Team',
    maintainer_email='sujinchoi17@gmail.com',
    description='AquaSweep robot motion controllers',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'controller_node = aqua_controller.controller_node:main',
            'mockup_controller_server = aqua_controller.mockup_controller_server:main',
            'mockup_robot_status = aqua_controller.mockup_robot_status:main',
        ],
    },
)
