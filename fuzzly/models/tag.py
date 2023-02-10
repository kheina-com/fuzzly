from enum import Enum, unique
from typing import Dict, List, Optional

from pydantic import BaseModel

from .post import PostId, PostIdValidator
from .user import UserPortable


class LookupRequest(BaseModel) :
	tag: Optional[str]


class TagsRequest(BaseModel) :
	_post_id_converter = PostIdValidator

	post_id: PostId
	tags: List[str]


class RemoveInheritance(BaseModel) :
	parent_tag: str
	child_tag: str


class InheritRequest(RemoveInheritance) :
	deprecate: Optional[bool] = False


class UpdateRequest(BaseModel) :
	tag: str
	name: Optional[str]
	tag_class: Optional[str]
	owner: Optional[str]
	description: Optional[str]
	deprecated: Optional[bool] = None


@unique
class TagGroupPortable(Enum) :
	artist: str = 'artist'
	subject: str = 'subject'
	sponsor: str = 'sponsor'
	species: str = 'species'
	gender: str = 'gender'
	misc: str = 'misc'


class TagPortable(str) :
	pass


class TagGroups(Dict[TagGroupPortable, List[TagPortable]]) :
	pass


class Tag(BaseModel) :
	tag: str
	owner: Optional[UserPortable]
	group: TagGroupPortable
	deprecated: bool
	inherited_tags: List[TagPortable]
	description: Optional[str]
	count: int
