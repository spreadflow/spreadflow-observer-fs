from setuptools import setup

tests_require = [
    'SpreadFlowCore[tests]',
    'SpreadFlowDelta[tests]',
    'SpreadFlowFormatBSON',
    'mock',
    'testtools'
]

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
        'SpreadFlowFormatBSON',
        'pathtools',
        'pymongo',
        'watchdog'
    ],
    tests_require=tests_require,
    extras_require={
        'tests': tests_require
    },
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
)
