.. highlight:: shell

############
Contributing
############

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

**********************
Types of Contributions
**********************

Report Bugs
===========

Report bugs at https://github.com/time-link/timelink-py/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
========

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
==================

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
===================

Timelink Python package could always use more documentation, whether as part of the
official Timelink Python package docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
===============

The best way to send feedback is to file an issue at https://github.com/time-link/timelink-py/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

************
Get Started!
************

Ready to contribute? Here's how to set up `timelink-py` for local development.

1. Fork the `timelink-py` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/timelink-py.git

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development::

    $ mkvirtualenv timelink
    $ cd timelink/
    $ python setup.py develop

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass flake8 and the
   tests, including testing other Python versions with tox::

    $ flake8 timelink tests
    $ python setup.py test or pytest
    $ tox

   To get flake8 and tox, just pip install them into your virtualenv.

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

***********************
Pull Request Guidelines
***********************

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python  3.7, 3.8, 3.9, and 3.10 and for PyPy. Check
   https://app.travis-ci.com/github/time-link/timelink-py/pull_requests
   and make sure that the tests pass for all supported Python versions.

**********
Deploying
**********

A reminder for the maintainers on how to deploy.

Tool documentation
==================

The Timelink package used as a template the `cookiecutter-pypackage`.

Check the documentation at https://github.com/audreyfeldroy/cookiecutter-pypackage
on how to install various tools used.

Check the release procedure documentation at https://cookiecutter-pypackage.readthedocs.io/en/latest/travis_pypi_setup.html

Requirements
============

Install development requirements with

.. code-block:: bash

   pip install -r requirements_dev.txt

Tox and multiple version of Python
==================================

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

Release process
===============

To release a new version:

.. code-block:: bash

   make lint                        # check code style
   make test                        # run the local test suite
   make coverage                    # check test coverage
   make test-all                    # test on different versions of python
   make docs                        # update the documentation
   git status                       # check if everything is commited
   bump2version [major|minor|patch] # update version
   git push
   git push --tags                  # will trigger travis build and deploy

Travis will then deploy to PyPI if tests pass.


Tips for maintaners
===================

Testing
-------

To run a subset of tests::

$ pytest tests/test_mhk_utilities.py

To run a subset of tests with tox::

$ tox -- tests/test_mhk_utilities.py

Tests related to the existence of a MHK installation

    Some tests are related to the existence of a MHK instalation on the same
    machine. The tests check for the existence of the file `.mhk` in the
    user home directory (~/.mhk).

    If MHK is installed rename ~/.mhk to run tests as if MHK is not present::

    $ mv ~/.mhk ~/.mhk_copy
    $ make test-all

    Once tests are run rename back to the original name::

    $ mv ~/.mhk_copy ~/.mhk
    $ make test-all

Code style (lint)
-----------------

To pass code style check

    `flake8` is used for code-style check,  with  the `flake8-bugbear`
    extension for extra checks, and a line length of 88 chars.

    We recommend using `black <https://black.readthedocs.io/en/stable/index.html>`_
    to reformat your code so that it passes the flake8 checks.

    `flake8` settings in `setup.cfg` ensure compatibility with `black` code style.

    To format and check the code::

    $ black timelink
    $ make lint


Updating documention
--------------------

Generate documentation
^^^^^^^^^^^^^^^^^^^^^^

To generate updated documentation use ``make docs``.

The generation is available at https://timelink-py.readthedocs.io/


Reference for markup used
^^^^^^^^^^^^^^^^^^^^^^^^^

Documentation is written *ReadTheDocs*, using the *reStructeredText* format
and the *Sphinx* formatter.
See:

    - `A Guide for Authors <https://docs.readthedocs.io/en/stable/guides/authors.html>`_
    - `Quick reference <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_
    - `Complete reference <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_

Documentation from docstrings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For docstrings in source code we use the Google style guide, which is more
legible during code editing than *ReStructured* text.

See:
    - `Examples of docstrings in Google style <https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html#example-google>`_
    - `Google style for Python, see section 3.8 <https://google.github.io/styleguide/pyguide.html>`_

Source code docstring in the Google format will be automatically rendered by
``make docs``. For details on how the docstring will be integrated with the
rest of the documention see:

    - `Napoleon extension to Sphinx <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_

Getting a list of *target* for cross-ref
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After doing ``make docs`` type:

    python -m sphinx.ext.intersphinx docs/_build/html/objects.inv


Using commits to document version history
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

List commits since the last version::

    $ git log $(git describe --tags --abbrev=0)..HEAD --oneline

or, for specific versions::

    $ git log v0.2.9..v0.3.0 --oneline




