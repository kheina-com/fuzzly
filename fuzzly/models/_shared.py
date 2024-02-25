from datetime import datetime
from enum import Enum, unique
from functools import lru_cache
from re import Pattern
from re import compile as re_compile
from secrets import token_bytes
from typing import Any, List, Optional, Type, Union

from kh_common.base64 import b64decode, b64encode
from pydantic import BaseModel, validator
from pydantic_core import core_schema


"""
This file contains any models that needs to be imported or used by multiple different modules.

Example: PostId is used by both user and post models
"""


################################################## MANY ##################################################

@unique
class Privacy(Enum) :
	public: str = 'public'
	unlisted: str = 'unlisted'
	private: str = 'private'
	unpublished: str = 'unpublished'
	draft: str = 'draft'


@unique
class Rating(Enum) :
	general: str = 'general'
	mature: str = 'mature'
	explicit: str = 'explicit'


@unique
class PostSort(Enum) :
	new: str = 'new'
	old: str = 'old'
	top: str = 'top'
	hot: str = 'hot'
	best: str = 'best'
	controversial: str = 'controversial'


################################################## POST ##################################################

class PostId(str) :
	"""
	automatically converts post ids in int, byte, or string format to their user-friendly str format.
	also checks for valid values.

	```python
	PostId(123)
	PostId('abcd1234')
	PostId(b'abc123')
	```
	"""

	__str_format__: Pattern = re_compile(r'^[a-zA-Z0-9_-]{8}$')
	__int_max_value__: int = 281474976710655


	def generate() -> 'PostId' :
		return PostId(token_bytes(6))


	@lru_cache(maxsize=128)
	def _str_from_int(value: int) -> str :
		return b64encode(int.to_bytes(value, 6, 'big')).decode()


	@lru_cache(maxsize=128)
	def _str_from_bytes(value: bytes) -> str :
		return b64encode(value).decode()


	def __new__(cls, value: Union[str, bytes, int]) :
		# technically, the only thing needed to be done here to utilize the full 64 bit range is update the 6 bytes encoding to 8 and the allowed range in the int subtype

		value_type: type = type(value)

		if value_type == PostId :
			return super(PostId, cls).__new__(cls, value)

		elif value_type == str :
			if not PostId.__str_format__.match(value) :
				raise ValueError('str values must be in the format of /^[a-zA-Z0-9_-]{8}$/')

			return super(PostId, cls).__new__(cls, value)

		elif value_type == int :
			# the range of a 48 bit int stored in a 64 bit int (both starting at min values)
			if not 0 <= value <= PostId.__int_max_value__ :
				raise ValueError(f'int values must be between 0 and {PostId.__int_max_value__:,}.')

			return super(PostId, cls).__new__(cls, PostId._str_from_int(value))

		elif value_type == bytes :
			if len(value) != 6 :
				raise ValueError('bytes values must be exactly 6 bytes.')

			return super(PostId, cls).__new__(cls, PostId._str_from_bytes(value))

		# just in case there's some weirdness happening with types, but it's still a string
		if isinstance(value, str) :
			if not PostId.__str_format__.match(value) :
				raise ValueError('str values must be in the format of /^[a-zA-Z0-9_-]{8}$/')

			return super(PostId, cls).__new__(cls, value)

		raise NotImplementedError('value must be of type str, bytes, or int.')


	def __get_pydantic_core_schema__(self, _: Type[Any]) -> core_schema.CoreSchema :
		return core_schema.no_info_after_validator_function(
			PostId,
			core_schema.any_schema(serialization=core_schema.str_schema()),
		)


	@lru_cache(maxsize=128)
	def int(self: 'PostId') -> int :
		return int.from_bytes(b64decode(self), 'big')

	__int__ = int


def _post_id_converter(value) :
	if value :
		return PostId(value)

	return value


PostIdValidator = validator('post_id', pre=True, always=True, allow_reuse=True)(PostId)


class Score(BaseModel) :
	up: int
	down: int
	total: int
	user_vote: int


class PostSize(BaseModel) :
	width: int
	height: int


################################################## USER ##################################################

@unique
class UserPrivacy(Enum) :
	public: str = 'public'
	private: str = 'private'


@unique
class Verified(Enum) :
	artist: str = 'artist'
	mod: str = 'mod'
	admin: str = 'admin'


class UserPortable(BaseModel) :
	_post_id_converter = validator('icon', pre=True, always=True, allow_reuse=True)(_post_id_converter)

	name: str
	handle: str
	privacy: UserPrivacy
	icon: Optional[PostId]
	verified: Optional[Verified]
	following: Optional[bool]


class Badge(BaseModel) :
	emoji: str
	label: str


class User(BaseModel) :
	_post_id_converter = validator('icon', 'banner', pre=True, always=True, allow_reuse=True)(_post_id_converter)

	name: str
	handle: str
	privacy: UserPrivacy
	icon: Optional[PostId]
	banner: Optional[PostId]
	website: Optional[str]
	created: datetime
	description: Optional[str]
	verified: Optional[Verified]
	following: Optional[bool]
	badges: List[Badge]

	def portable(self: 'User') -> UserPortable :
		return UserPortable(
			name = self.name,
			handle = self.handle,
			privacy = self.privacy,
			icon = self.icon,
			verified = self.verified,
			following = self.following,
		)


################################################## SETS ##################################################

class SetId(str) :
	"""
	automatically converts set ids in int, byte, or string format to their user-friendly str format.
	also checks for valid values.

	```python
	SetId(123)
	SetId('abc-123')
	SetId(b'abcde')
	```
	"""

	__str_format__: Pattern = re_compile(r'^[a-zA-Z0-9_-]{7}$')
	__int_max_value__: int = 1099511627775


	def generate() -> 'SetId' :
		return SetId(token_bytes(5))


	@lru_cache(maxsize=128)
	def _str_from_int(value: int) -> str :
		return b64encode(int.to_bytes(value, 5, 'big')).decode()


	@lru_cache(maxsize=128)
	def _str_from_bytes(value: bytes) -> str :
		return b64encode(value).decode()


	def __new__(cls, value: Union[str, bytes, int]) :
		# technically, the only thing needed to be done here to utilize the full 64 bit range is update the 4 bytes encoding to 8 and the allowed range in the int subtype

		value_type: type = type(value)

		if value_type == SetId :
			return super(SetId, cls).__new__(cls, value)

		elif value_type == str :
			if not SetId.__str_format__.match(value) :
				raise ValueError('str values must be in the format of /^[a-zA-Z0-9_-]{7}$/')

			return super(SetId, cls).__new__(cls, value)

		elif value_type == int :
			# the range of a 40 bit int stored in a 64 bit int (both starting at min values)
			if not 0 <= value <= SetId.__int_max_value__ :
				raise ValueError(f'int values must be between 0 and {SetId.__int_max_value__:,}.')

			return super(SetId, cls).__new__(cls, SetId._str_from_int(value))

		elif value_type == bytes :
			if len(value) != 5 :
				raise ValueError('bytes values must be exactly 5 bytes.')

			return super(SetId, cls).__new__(cls, SetId._str_from_bytes(value))

		# just in case there's some weirdness happening with types, but it's still a string
		if isinstance(value, str) :
			if not SetId.__str_format__.match(value) :
				raise ValueError('str values must be in the format of /^[a-zA-Z0-9_-]{7}$/')

			return super(SetId, cls).__new__(cls, value)

		raise NotImplementedError('value must be of type str, bytes, or int.')


	def __get_pydantic_core_schema__(self, _: Type[Any]) -> core_schema.CoreSchema :
		return core_schema.no_info_after_validator_function(
			SetId,
			core_schema.any_schema(serialization=core_schema.str_schema()),
		)


	@lru_cache(maxsize=128)
	def int(self: 'SetId') -> int :
		return int.from_bytes(b64decode(self), 'big')

	__int__ = int


SetIdValidator = validator('set_id', pre=True, always=True, allow_reuse=True)(SetId)
