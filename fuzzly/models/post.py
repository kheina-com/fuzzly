from datetime import datetime
from enum import Enum, unique
from typing import Any, Dict, List, Optional, Union

from kh_common.base64 import b64encode
from pydantic import BaseModel, validator

from ._shared import PostId, PostIdValidator, PostSize, PostSort, Privacy, Rating, Score, UserPortable, _post_id_converter


class VoteRequest(BaseModel) :
	_post_id_validator = PostIdValidator

	post_id: PostId
	vote: Union[int, None]


class TimelineRequest(BaseModel) :
	count: Optional[int] = 64
	page: Optional[int] = 1


class BaseFetchRequest(TimelineRequest) :
	sort: PostSort


class FetchPostsRequest(BaseFetchRequest) :
	tags: Optional[List[str]]


class FetchCommentsRequest(BaseFetchRequest) :
	_post_id_validator = PostIdValidator

	post_id: PostId


class GetUserPostsRequest(BaseModel) :
	handle: str
	count: Optional[int] = 64
	page: Optional[int] = 1


class MediaType(BaseModel) :
	file_type: str
	mime_type: str


@unique
class TagGroupPortable(Enum) :
	artist: str = 'artist'
	subject: str = 'subject'
	sponsor: str = 'sponsor'
	species: str = 'species'
	gender: str = 'gender'
	misc: str = 'misc'


class TagGroups(Dict[TagGroupPortable, List[str]]) :
	pass


def _thumbhash_converter(value: Any) -> Any :
	if value and not isinstance(value, str) :
		return b64encode(value)

	return value


class Post(BaseModel) :
	_post_id_validator = PostIdValidator
	_post_id_converter = validator('parent', pre=True, always=True, allow_reuse=True)(_post_id_converter)
	_thumbhash_converter = validator('thumbhash', pre=True, always=True, allow_reuse=True)(_thumbhash_converter)

	post_id: PostId
	title: Optional[str]
	description: Optional[str]
	user: UserPortable
	score: Optional[Score]
	rating: Rating
	parent: Optional[PostId]
	privacy: Privacy
	created: Optional[datetime]
	updated: Optional[datetime]
	filename: Optional[str]
	media_type: Optional[MediaType]
	size: Optional[PostSize]
	blocked: bool
	thumbhash: Optional[str]
