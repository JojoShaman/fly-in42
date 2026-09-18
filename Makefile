MAPS_URL = https://cdn.intra.42.fr/document/document/55008/maps.tar.gz

maps:
	@if [ ! -d maps ]; then \
		curl -sSL -o maps.tar.gz $(MAPS_URL) && \
		tar xzf maps.tar.gz && \
		rm -rf maps.tar.gz; \
	fi

install:
	poetry install

run: maps
	python3 src/main.py

debug:
	python3 -m pdb src/main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name "maps" -exec rm -rf {} +
	find . -name ".DS_Store" -delete

lint:
	-flake8 . --exclude=.venv
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	-flake8 . --exclude=.venv
	mypy . --strict

.PHONY: install run debug clean lint lint-strict