.PHONY: init
init:
	@pipenv install --dev

.PHONY: clean
clean:
	@rm -rf build dist .pytest_cache .tox
	@find . -name "*.egg" -exec rm -rf {} +
	@find . -name "*.egg-info" -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -exec rm -rf {} +
