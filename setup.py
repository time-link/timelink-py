#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['typer~=0.4.0', ]

test_requirements = ['pytest>=3', ]

description = "Timelink is an information system for person related information collected from historical sources. "  # noqa

setup(
    author="Joaquim Ramos de Carvalho",
    author_email='joaquimcarvalho@ipm.edu.mo',
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    description=description,
    entry_points={
        'console_scripts': [
            'timelink=timelink.cli:app',
        ],
    },
    project_urls={
         'Documentation': 'https://timelink-py.readthedocs.io/',
    },
    install_requires=[
        'typer~=0.4.0',
        'fastapi~=0.103.0',
        'sqlalchemy~=2.0.0',
        'pydantic~=2.0.0',
        'python-dotenv~=0.21.0',
        'python-box~=5.3.0',
        'psycopg2-binary==2.9.6',
        'py-markdown-table==0.3.3',
        'pandas~=2.0.0',
        'docker~=6.0.0',
        'jsonrpcclient~=4.0.0',
        'ipython~=8.0.0'
        

    ],
    license="MIT license",
    long_description= description + '\n\n' + history,
    long_description_content_type = 'text/x-rst',
    include_package_data=True,
    keywords='timelink',
    name='timelink',
    packages=find_packages(include=['timelink', 'timelink.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/time-link/timelink-py',
    version='1.0.0',
    zip_safe=False,
)
