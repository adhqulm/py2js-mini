py2js-mini

A tiny Python → JavaScript transpiler

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

It takes a subset of Python code, lowers it into a custom intermediate form, 
and emits equivalent JavaScript that runs with a small Python-like runtime (pyrt.js).

---------

## Features:

- Functions & arguments
- Positional args, defaults, *args, **kwargs
- Classes & methods
- Exceptions (try/except/finally)
- Loops & conditionals
- for, while, for/else, while/else
- Slicing & tuples
- Strings & list operations
- Dict iteration
- Imports & with-contexts
- Golden test suite

--------

## Installation:

Clone the repo and install in editable mode:

git clone https://github.com/adhqulm/py2js-mini.git
cd py2js-mini
pip install -e .

---------

## Limitations:

This is a demo transpiler, not a full Python implementation.
Currently unsupported:
Generators (yield)
Async / await
Closures & cell variables
Full standard library

