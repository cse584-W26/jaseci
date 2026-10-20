PYTHON ?= python
LATEX ?= pdflatex

.PHONY: all pdf regenerate assets check bundle clean FORCE
all: main.pdf

pdf: main.pdf

assets:
	$(PYTHON) prepare.py

regenerate: assets main.pdf

main.pdf: main.tex references.bib acmart.cls pvldb.sty ACM-Reference-Format.bst FORCE
	mkdir -p build
	$(LATEX) -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/latex-pass1.txt
	bibtex build/main > build/bibtex.txt
	$(LATEX) -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/latex-pass2.txt
	$(LATEX) -interaction=nonstopmode -halt-on-error -output-directory=build main.tex > build/latex-pass3.txt
	cp build/main.pdf main.pdf

check: main.pdf
	$(PYTHON) validate.py

bundle:
	$(PYTHON) bundle.py

clean:
	rm -f build/main.aux build/main.bbl build/main.blg build/main.log build/main.out build/main.pdf build/latex-pass1.txt build/latex-pass2.txt build/latex-pass3.txt build/bibtex.txt
