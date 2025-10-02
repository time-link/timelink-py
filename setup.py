#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['typer>=0.9.0', ]

test_requirements = ['pytest>=8', ]

description = "Timelink is an information system for person related information collected from historical sources. "  # noqa

long_description = readme + '\n\n' + history

# It's a good practice to define your requirements in a list
# and then pass that list to setup().
# This list should contain the packages your project needs to run.
# Avoid pinning to exact versions unless you have a specific reason.
requirements = [
    'typer>=0.9.0',
    'fastapi>=0.100.0',
    'matplotlib>=3.7.0',
    'sqlalchemy>=2.0',
    'sqlalchemy-utils>=0.41.0',
    'alembic>=1.10.0',
    'pydantic>=2.0',
    'pydantic-settings>=2.0',
    'python-dotenv>=1.0',
    'python-box>=7.0',
    'python-multipart>=0.0.6',
    'psycopg2-binary>=2.9.0',
    'py-markdown-table>=0.3.0',
    'pandas>=2.0',
    'docker>=6.0',
    'jsonrpcclient>=4.0',
    'ipython>=8.10',
    'uvicorn>=0.23.0'
]

setup(
    author="Joaquim Ramos de Carvalho",
    author_email='joaquimcarvalho@mpu.edu.mo',
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
            'tmlk=timelink.cli:app',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=long_description,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='timelink',
    name='timelink',
    packages=find_packages(include=['timelink', 'timelink.*']),
    package_data={
        'timelink': ['migrations/versions/*.py'],
    },
    project_urls={
        'Documentation': 'https://timelink-py.readthedocs.io/',
    },
    test_suite='tests',
    # Use extras_require for test dependencies.
    # This is the modern approach.
    extras_require={
        'test': test_requirements,
    },
    url='https://github.com/time-link/timelink-py',
    version='1.1.26',
    zip_safe=False,
)
