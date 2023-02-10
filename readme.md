<p align="center">
	<img src="https://github.com/kheina-com/fuzzly/raw/main/logo.png" alt="fuzzly Logo">
	<br>
	<a href="https://github.com/kheina-com/fuzzly/actions?query=workflow%3Apython-package+event%3Apush+branch%3Amain">
		<img src="https://github.com/kheina-com/fuzzly/actions/workflows/python-package.yml/badge.svg?branch=main" alt="python-package workflow">
	</a>
	<a href="https://pypi.org/project/fuzzly">
		<img src="https://img.shields.io/pypi/v/fuzzly?color=success&label=pypi%20package" alt="pypi package version">
	</a>
</p>
<p align="center">
	A python client library for <a href="https://dev.fuzz.ly/docs">fuzz.ly</a>
</p>


# Installation
```bash
pip install fuzzly
```

# Usage
```python
from fuzzly import FuzzlyClient
from fuzzly.models.post import Post

# if you have a bot token, make sure you initialize the client with your token
token: str = 'aGV5IG1hbi4gaXQncyB3ZWlyZCB0aGF0IHlvdSBsb29rZWQgYXQgdGhpcywgYnV0IHRoaXMgaXNuJ3QgYSByZWFsIHRva2Vu'
client: FuzzlyClient = FuzzlyClient(token)

post: Post = await client.post('abcd1234')
```

# Documentation
Official documentation is hosted using [Github's Wiki function](./wiki). Additionally, each subfolder in this repository has it's own readme with a brief overview of that directory's contents, purpose, and usage like the one above.


# Development
Fork the parent repository at https://github.com/kheina-com/fuzzly and edit like any other python project.  
Tests are run with `pytest` in the command line and input sorting is run via `isort .`

# License
This work is licensed under the [Mozilla Public License 2.0](https://choosealicense.com/licenses/mpl-2.0/), allowing for public, private, and commercial use so long as access to this library's source code is provided. If this library's source code is modified, then the modified source code must be licensed under the same license or an [applicable GNU license](https://www.mozilla.org/en-US/MPL/2.0/#1.12) and made publicly available.
