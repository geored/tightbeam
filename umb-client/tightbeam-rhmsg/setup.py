# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='rhmsg',
    description='A Python module interacting with Unified Message Bus',
    author='Chenxiong Qi',
    author_email='cqi@redhat.com',
    version='0.9',
    license='GPLv3',
    url='https://code.engineering.redhat.com/gerrit/gitweb?p=rhmsg.git;a=summary',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'amq-producer = rhmsg.cli.amqproducer:main',
            'amq-consumer = rhmsg.cli.amqconsumer:main',
            'rhmsg-replay = rhmsg.cli.replay:main',
            ]
        },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ]
    )
