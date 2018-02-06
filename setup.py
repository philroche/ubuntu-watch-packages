import os
from setuptools import find_packages, setup
from glob import glob
from os.path import basename
from os.path import splitext

reqs_path = os.path.join(os.path.dirname(__file__), 'src/requirements.txt')

with open(reqs_path, 'r') as req_file:
    dependencies = req_file.readlines()

setup(
    name='ubuntu-watch-packages',
    version='0.1',
    install_requires=dependencies,
    url='',
    license='',
    author='philroche',
    author_email='phil.roche@canonical.com',
    description='Helpful utility to watch specified packages, using rmadison, '
                'in the ubuntu archive for transition between archive pockets',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ubuntu-watch-packages = '
            'ubuntu_watch_packages.ubuntu_watch_packages:ubuntu_watch_packages',
        ],
    },
)
