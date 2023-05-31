from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from ._shared import PostId, SetId, SetIdValidator, UserPortable, UserPrivacy
from .post import Post


class Set(BaseModel) :
	_set_id_validator = SetIdValidator

	set_id: SetId
	owner: UserPortable
	count: int
	title: Optional[str]
	description: Optional[str]
	privacy: UserPrivacy
	created: datetime
	updated: datetime


class SetNeighbors(BaseModel) :

	first: Optional[Post]
	"""
	the first post in the set
	"""

	last: Optional[Post]
	"""
	the last post in the set
	"""

	index: int
	"""
	the central index post around which the neighbors exist in the set
	"""

	before: List[Optional[Post]]
	"""
	neighbors before the index are arranged in descending order such that the first item in the list is always index - 1 where index is PostNeighbors.index

	EX:
	before: [index - 1, index - 2, index - 3, ...]
	"""

	after: List[Optional[Post]]
	"""
	neighbors after the index are arranged in ascending order such that the first item in the list is always index + 1 where index is PostNeighbors.index

	EX:
	after: [index + 1, index + 2, index + 3, ...]
	"""


class PostSet(BaseModel) :
	set_id: SetId
	owner: UserPortable
	title: Optional[str]
	description: Optional[str]
	privacy: UserPrivacy
	created: datetime
	updated: datetime
	post_id: PostId
	neighbors: SetNeighbors
