from setuptools import find_packages, setup

from fuzzly import __version__


setup(
	name='fuzzly',
	version=__version__,
	description='Fuzz.ly client library for Python3',
	long_description=open('readme.md').read(),
	long_description_content_type='text/markdown',
	author='kheina',
	url='https://github.com/kheina-com/fuzzly',
	packages=find_packages(exclude=['tests']),
	install_requires=list(filter(None, map(str.strip, open('requirements.txt').read().split()))),
	python_requires='>=3.9',
	license='Mozilla Public License 2.0',
)
