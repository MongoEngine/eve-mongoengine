.PHONY: clean-pyc clean-build docs

COMMIT_ID = $(shell git rev-parse HEAD)
COMMIT_MSG = $(shell git log -1 --pretty=%B)
VERSION = $(shell grep "current_version" .bumpversion.cfg | cut -d' ' -f3-)

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "celery - start celery beat and worker"
	@echo "coverage - run coverage test"
	@echo "config - install dev environment"
	@echo "test - run tests"
	@echo "translate - generate localization files"
	@echo "docs - generate Sphinx HTML documentation, including API docs"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr htmlcov
	rm -f *.db
	rm -f *.mo

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +


config: clean
	pipenv install --dev

format:
	pipenv run black .

typecheck:
	pipenv run pytype app

lint:
	pipenv run black --check .

test: lint
	pipenv run python -m unittest

debug:
	echo tag is $(COMMIT_MSG)

bumpversion:
	pipenv run bumpversion minor


auto-update-pipenv:
	git config --global user.name 'GitHub'
	git config --global user.email 'noreply@github.com'
	git checkout -B automated-package-update
	source .env; pipenv update --dev
	git commit -a -m 'automated package update'
	git push origin automated-package-update