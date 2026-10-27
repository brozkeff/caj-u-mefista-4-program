PYTHON ?= python3
.PHONY: build xml sources verify clean
build:
	$(PYTHON) scripts/build.py
sources:
	$(PYTHON) scripts/build.py --skip-pdf
xml:
	$(PYTHON) scripts/pentabarf.py
verify:
	$(PYTHON) scripts/verify.py
clean:
	rm -rf build/pdf build/qr
	rm -f tex/generated/*.tex build/*.log
