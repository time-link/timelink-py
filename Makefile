.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint: ## check style with flake8
	flake8 timelink tests

test-loop: ## run tests quickly with the default Python
	for file in tests/*.py; do \
		pytest $$file $(ARGS); \
	done

test: ## run tests quickly with the default Python
	pytest --rootdir=tests $(ARGS)
	py.test --nbval tests/timelink-home/projects/test-project/notebooks/test*


test-nb: ## test notebooks only
	py.test --nbval tests/timelink-home/projects/test-project/notebooks/test*

test-all: ## run tests on every Python version with tox
	tox

profile:
	pytest --profile $(ARGS)
	snakeviz prof/combined.prof

coverage: ## check code coverage quickly with the default Python
	coverage run --source timelink -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

docs: export SPHINX_APIDOC_OPTIONS=no-undoc-members,no-show-inheritance
docs: ## generate Sphinx HTML documentation, including API docs
	rm -f docs/timelink.rst
	rm -f docs/modules.rst

	sphinx-apidoc --module-first --doc-project "Timelink source documentation" -o docs/ timelink
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst;*.py;*.md' -c '$(MAKE) -C docs html' -R -D .

release: dist ## package and upload a release
	twine check dist/*
	twine upload dist/* --verbose

dist: clean ## builds source and wheel package
	python -m build
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	pip install .
