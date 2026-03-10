from setuptools import setup
import os
from glob import glob

package_name = 'artbot_sim'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        # 1. Launch Files
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        
        # 2. URDF Files
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        
        # 3. Config Files (CRITICAL: This fixes the Gazebo crash)
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),

        # 4. Scripts (CRITICAL: This fixes "drive_circle.py not found")
        (os.path.join('lib', package_name), glob('scripts/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # If you want to run them as commands, list them here, 
            # but the copy-scripts line above usually handles the executables.
        ],
    },
)