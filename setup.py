import os
import subprocess
from sys import platform
from setuptools import setup
from distutils.command.build import build

BASEPATH = os.path.dirname(os.path.abspath(__file__))

class BinaryBuild(build):
    def run(self):
        # run original build code
        build.run(self)

        if platform == 'darwin':
            ext_path = os.path.join(BASEPATH, 'ext/spotlight')
            ext_target = os.path.join(ext_path, 'build/spreadflow-observer-fs-spotlight')
        else:
            return

        def compile():
            subprocess.call(('make', 'V=' + str(self.verbose)), cwd=ext_path)

        self.execute(compile, [], 'Compiling native extension')

        # copy resulting tool to library build folder
        bin_dir = os.path.join(self.build_lib, 'bin')
        self.mkpath(bin_dir)
        if not self.dry_run:
            self.copy_file(ext_target, bin_dir)


setup(
    name='SpreadFlowObserverFS',
    version='0.0.1',
    description='Filesystem observer for SpreadFlow metadata extraction and processing engine',
    author='Lorenz Schori',
    author_email='lo@znerol.ch',
    url='https://github.com/znerol/spreadflow-observer-fs',
    packages=[
        'spreadflow_observer_fs',
        'spreadflow_observer_fs.test',
        'twisted.plugins'
    ],
    package_data={
        'twisted.plugins': [
            'twisted/plugins/spreadflow_observer_fs_endpoint.py',
        ]
    },
    entry_points={
        'console_scripts': [
            'spreadflow-observer-fs-default = spreadflow_observer_fs.script:main',
        ]
    },
    install_requires=[
        'SpreadFlowCore',
        'pathtools',
        'pymongo',
        'watchdog'
    ],
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Multimedia'
    ],
    cmdclass={
        'build': BinaryBuild,
    }
)
