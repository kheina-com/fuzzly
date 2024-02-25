from dataclasses import dataclass
from enum import Enum
from inspect import _empty
from typing import Any, Optional

from fuzzly import Client, FuzzlyClient


client: FuzzlyClient = FuzzlyClient()
c: Client = Client()

funcs: list[str] = [i for i in client.__dir__() if not i.startswith('_') and i not in set(c.__dir__())]
models: list[type] = []

bullet = "\n- "

client_header = """[See the home page for client setup](.)

# Client Methods
Notice that all client functions are `async`. This is because http requests are made under the hood and they are done in parallel with other requests."""
models_header = """[See the client page for how to retrieve and use these models](./Client)"""


def docstrip(doc: str) -> str :
	doc = doc.strip('\n\r')
	indent = len(doc) - len(doc.lstrip('\t'))
	return '\n'.join(docstr.removeprefix('\t' * indent) for docstr in doc.split('\n')).strip()


def model_name(model: type) -> str :
	module = model.__module__

	if module.endswith('._shared') :
		module = module[:-8]

	return f'{module}.{model.__name__}'


def model_link(model: type, local: bool = False) -> str :
	if local :
		return '#' + model_name(model).replace('.', '').lower()
	return './Models#' + model_name(model).replace('.', '').lower()


def valuestr(value: Any) -> str :
	for cls in getattr(value.__class__, '__mro__', []) :
		if cls == Enum :
			return f'{value.__class__.__name__}.{value.name}'

		if cls in { int, float, str } :
			return str(value)

	raise ValueError(f'no known conversion for {value.__class__}')


def modelstr(model: type, link: bool = False) -> str :
	m = model
	fmt = '{}'
	name = m.__name__
	
	if hasattr(model, '__args__') :
		m = model.__args__[0]
		fmt = f'{model.__name__}[{{}}]'
		name = modelstr(m)

	if link :
		return fmt.format(f'<a href="{model_link(m)}">{name}</a>')

	else :
		return fmt.format(name)


@dataclass
class Param :
	name: str
	type: str
	default: Optional[str] = None

	def doc(self) -> str :
		doc = f'{self.name}: '

		if 'fuzzly' in self.type.__module__ :
			models.append(self.type)

			doc += modelstr(self.type, link=True)
			doc = f'<code>{doc}</code>'

		else :
			doc += modelstr(self.type)
			doc = f'`{doc}`'

		if self.default :
			doc += f' (optional, default: `{valuestr(self.default)}`)'

		return doc

	def __str__(self) -> str :
		if self.default :
			return f'{self.name}: {modelstr(self.type)} = {valuestr(self.default)}'

		else :
			return f'{self.name}: {modelstr(self.type)}'


def funcdoc(funcstr: str) -> str :
	func = getattr(client, funcstr)
	docstr = docstrip(func.__doc__)

	params: list[Param] = []
	__omit__ = { 'self', 'auth' }
	for key, param in func.__signature__.parameters.items() :
		if key in __omit__ :
			continue

		p = Param(name=param.name, type=param.annotation)
		if param.default != _empty :
			p.default = param.default

		params.append(p)

	r = func.__signature__.return_annotation
	if 'fuzzly' in r.__module__ :
		models.append(r)
	if hasattr(r, '__args__') :
		for m in r.__args__ :
			if 'fuzzly' in m.__module__ :
				models.append(m)

	title = f'({func.__self__.__class__.__name__}).{func.__name__}({", ".join([i.name for i in params])}) -> {modelstr(r)}'

	doc = f'## {title}\n{docstr}'

	if params :
		doc += f'\n\n#### params{bullet}{bullet.join(map(Param.doc, params))}'

	return f'{doc}\n\n#### returns\n- <code>{modelstr(r, link=True)}</code>'


def model_subtypes(model: type) -> list[type] :
	subtypes: list[type] = []

	if 'fuzzly' in model.__module__ :
		subtypes.append(model)

	if hasattr(model, '__args__') :
		for m in model.__args__ :
			subtypes += model_subtypes(m)

	return subtypes


def modeldoc(model: type) -> str :
	doc = ""
	if model.__doc__ :
		doc = docstrip(model.__doc__)

	classdef = f'```python\nclass {model.__name__}'
	if len(model.__mro__) > 2 :
		classdef += f'({model.__mro__[1].__name__})'
	classdef += ':'

	subtypes: list[type] = []

	if hasattr(model, 'model_fields') :
		if doc :
			doc += '\n\n'
		doc += classdef

		for name, field in model.model_fields.items() :
			s = model_subtypes(field.annotation)
			models.extend(s)
			subtypes.extend(s)

			doc += f'\n\t{name}: {modelstr(field.annotation)}'
		doc += '\n```'

	if issubclass(model, Enum) :
		if doc :
			doc += '\n\n'
		doc += classdef

		for member in model.__members__.values() :
			doc += f'\n\t{member.name}: {type(member.value).__name__} = \'{member.value}\''

		doc += '\n```'

	_completed_subtypes: set[type] = set()
	if subtypes :
		doc += '\n\n#### subtypes'
		for subtype in subtypes :
			if subtype in _completed_subtypes :
				continue

			doc += f'{bullet}[`{subtype.__name__}`]({model_link(subtype, local=True)})'
			_completed_subtypes.add(subtype)

	return f'### `{model_name(model)}`\n{doc}'


with open('client.md', 'w') as file :
	file.write(client_header + '\n\n\n' + '\n\n\n'.join(map(funcdoc, funcs)))

with open('models.md', 'w') as file :
	doc = models_header
	_completed_models: set[type] = set()
	for model in models :
		if model in _completed_models :
			continue

		doc += '\n\n\n' + modeldoc(model)
		_completed_models.add(model)

	file.write(doc)
