# -*- coding: utf-8 -*-
import os
import sys
from setuptools import setup
from setuptools import find_packages

version = '0.6'

install_requires = ['waitress', 'webob']
test_requires = [
    'pytest', 'webtest', 'coverage', 'coveralls', 'WSGIProxy2',
]

if sys.version_info[:2] < (3, 0):
    install_requires.extend([
        'trollius',
        'futures',
    ])
    test_requires.extend(['mock'])
elif sys.version_info[:2] < (3, 3):
    install_requires.append('trollius')
    test_requires.append('mock')
elif sys.version_info[:2] < (3, 4):
    install_requires.append('asyncio')


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


setup(
    name='aiowsgi',
    version=version,
    description="minimalist wsgi server using asyncio",
    long_description=read('README.rst'),
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='',
    author='Gael Pasgrimaud',
    author_email='gael@gawel.org',
    url='https://github.com/gawel/aiowsgi/',
    license='MIT',
    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require={
        'test': test_requires,
    },
    entry_points="""
    [paste.server_runner]
    main = aiowsgi:serve_paste
    [console_scripts]
    aiowsgi-serve = aiowsgi:run
    """,
)
