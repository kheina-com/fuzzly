from datetime import datetime
from enum import Enum, unique
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, validator

from ._shared import PostId, PostIdValidator, PostSize, Score, UserPortable, _post_id_converter


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


class Post(BaseModel) :
	_post_id_validator = PostIdValidator
	_post_id_converter = validator('parent', pre=True, always=True, allow_reuse=True)(_post_id_converter)

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
