from setuptools import find_packages, setup

package_name = 'nidar_frontier_exploration'

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
    maintainer='isro',
    maintainer_email='aarushgupta289@gmail.com',
    description='Detect and visualize occupancy-grid frontiers and evaluate free-space clearance.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'frontier_node = nidar_frontier_exploration.frontier_node:main',
        ],
    },
)
