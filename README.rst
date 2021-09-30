=======================
Timelink Python package
=======================


.. image:: https://img.shields.io/pypi/v/timelink.svg
        :target: https://pypi.python.org/pypi/timelink

.. image:: https://api.travis-ci.com/time-link/timelink-py.svg?branch=main
        :target: https://travis-ci.com/joaquimrcarvalho/timelink

.. image:: https://readthedocs.org/projects/timelink-py/badge/?version=latest
        :target: https://timelink-py.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

* Free software: MIT license
* Documentation: https://timelink.readthedocs.io.


Features
--------


* Pythonic representation of Kleio groups, easing generation of Kleio
  file from data in other formats. See :py:mod:`timelink.kleio.groups`
* Utility functions for acessing MHK instalation,
  including database access. See :py:mod:`timelink.mhk.utilities`
* CLI tool. See :py:mod:`timelink.cli`

See package documentation :py:mod:`timelink`

Development notes
-----------------

Tool documentation
^^^^^^^^^^^^^^^^^^

The Timelink package used as a template the `cookiecutter-pypackage`.

Check the documentation at https://github.com/audreyfeldroy/cookiecutter-pypackage
on how to install various tools used.

Check the release procedure documentation at https://cookiecutter-pypackage.readthedocs.io/en/latest/travis_pypi_setup.html

Requirements
^^^^^^^^^^^^

Install development requirements with

    pip install -r requirements_dev.txt

Release process
^^^^^^^^^^^^^^^

If using `tox` to test with different versions of Python then
you need to have the various Python interpreters installed.

The `tox.ini` file specifies which version of Python will be used for
tests. `pyenv` is used to install the different version.

On MacOS you may get a zlib related error while installing Python versions with pyenv.
Check  https://stackoverflow.com/questions/50036091/pyenv-zlib-error-on-macos

The solution for us was:

.. code-block:: bash

   brew install zlib
   export LDFLAGS="-L/usr/local/opt/zlib/lib"
   export CPPFLAGS="-I/usr/local/opt/zlib/include"
   pyenv install 3.7.2

If `tox` complains of not finding the different Python version
you need to reinstall tox after installing locally the various versions.
See  https://brandonrozek.com/blog/pyenvtox/

Example:

.. code-block:: bash

   pyenv local 3.6.0 3.7.0 3.8.0
   pip install tox

The target
*test-all* triggers the test in the various versions.

To release a new version:

.. code-block:: bash

   make lint       # check code style
   make test       # run the local test suite
   make coverage   # check test coverage
   make test-all   # run the test on various version of python
   make docs       # update the documentation

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

