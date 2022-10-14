.PHONY: test
test:
	@pipenv run check
	@pipenv run test

.PHONY: fix
fix:
	@pipenv run isort tests randomjson
	@pipenv run black tests randomjson

.PHONY: clean
clean:
	@rm -rf build dist .pytest_cache .tox
	@find . -name "*.egg" -exec rm -rf {} +
	@find . -name "*.egg-info" -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -exec rm -rf {} +

.PHONY: develop
develop:
	@python setup.py develop

.PHONY: install
install: clean
	@python setup.py install

.PHONY: dist
dist: clean
	@python setup.py sdist
	@ls -al dist

.PHONY: init
init:
	@pipenv install --dev
