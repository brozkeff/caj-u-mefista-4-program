PYTHON ?= python3
.PHONY: build xml sources verify test clean
build:
	$(PYTHON) scripts/build.py
sources:
	$(PYTHON) scripts/build.py --skip-pdf
xml:
	$(PYTHON) scripts/pentabarf.py
verify:
	$(PYTHON) scripts/verify.py
test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'
	node --test tests/schedule-links.cjs
clean:
	rm -rf build/pdf build/qr
	rm -f tex/generated/*.tex build/*.log
