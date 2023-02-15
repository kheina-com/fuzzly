from asyncio import Task, ensure_future
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set, Tuple

from kh_common.auth import KhUser
from kh_common.caching import AerospikeCache, ArgsCache
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.gateway import Gateway
from pydantic import BaseModel, validator

from ..client import Client
from ..constants import ConfigHost, PostHost, TagHost, UserHost
from ._database import DBI
from ._shared import Badge, PostId, PostSize, User, UserPortable, UserPrivacy, Verified, _post_id_converter
from .config import UserConfig
from .post import MediaType, Post, PostId, PostSize, PostSort, Privacy, Rating, Score
from .tag import Tag, TagGroupPortable, TagGroups
from .user import UserPortable


# each internal endpoint will have it's own exported kvs so that they can be overwritten or imported by users
UserConfigKVS: KeyValueStore = KeyValueStore('kheina', 'configs')
TagKVS: KeyValueStore = KeyValueStore('kheina', 'tags')
UserKVS: KeyValueStore = KeyValueStore('kheina', 'users', local_TTL=60)
PostKVS: KeyValueStore = KeyValueStore('kheina', 'posts')

# internal functions sometimes need to interact with the db, this is done through this interface
DB: DBI = DBI()


class _InternalClient(Client) :
	"""
	There's a lot of api calls that needs to occur within internal models to work correctly.
	Those are set up within this client so that the main client in the root does not break without internal auth/kvs access
	"""

	_user_config: Gateway = Gateway(ConfigHost + '/i1/user/{user_id}', UserConfig, method='GET')
	_post_tags: Gateway = Gateway(TagHost + '/v1/post/{post_id}', TagGroups, method='GET')
	_user_posts: Gateway  # this will be assigned later
	_post: Gateway  # this will be assigned later
	_user: Gateway  # this will be assigned later
	_tag: Gateway  # this will be assigned later


	def __hash__(self: '_InternalClient') -> int :
		return 0


	@AerospikeCache('kheina', 'configs', 'user.{user_id}', read_only=True, _kvs=UserConfigKVS)
	@Client.authenticated
	async def user_config(self: Client, user_id: int, auth: str = None) -> UserConfig :
		return await _InternalClient._user_config(user_id=user_id, auth=auth)


	@AerospikeCache('kheina', 'users', '{user_id}', read_only=True, _kvs=UserKVS)
	@Client.authenticated
	async def user(self: Client, user_id: int, auth: str = None) -> 'InternalUser' :
		return await _InternalClient._user(user_id=user_id, auth=auth)


	@AerospikeCache('kheina', 'tags', 'post.{post_id}', read_only=True, _kvs=TagKVS)
	@Client.authenticated
	async def post_tags(self: Client, post_id: PostId, auth: str = None) -> TagGroups :
		return await _InternalClient._post_tags(post_id=post_id, auth=auth)


	@AerospikeCache('kheina', 'posts', '{post_id}', read_only=True, _kvs=PostKVS)
	@Client.authenticated
	async def post(self: Client, post_id: PostId, auth: str = None) -> 'InternalPost' :
		return await _InternalClient._post(post_id=post_id, auth=auth)


	# not cached (should be?)
	@Client.authenticated
	async def user_posts(self: Client, user_id: int, sort: PostSort = PostSort.new, count: int = 64, page: int = 1, auth: str = None) -> 'InternalPost' :
		return await _InternalClient._user_posts({ 'sort': sort.name, 'count': count, 'page': page }, user_id=user_id, auth=auth)


	# this function routes directly to the db, so auth is unnecessary
	@AerospikeCache('kheina', 'users', 'handle.{handle}', _kvs=UserKVS)  # also notice that readonly is omitted
	async def user_handle_to_id(self: Client, handle: str) -> int :
		return await DB._handle_to_user_id(handle)


class BlockTree :

	def dict(self: 'BlockTree') :
		result = { }

		if not self.match and not self.nomatch :
			result['end'] = True

		if self.match :
			result['match'] = { k: v.dict() for k, v in self.match.items() }

		if self.nomatch :
			result['nomatch'] = { k: v.dict() for k, v in self.nomatch.items() }

		return result


	def __init__(self: 'BlockTree') :
		self.tags: Set[str] = None
		self.match: Dict[str, BlockTree] = None
		self.nomatch: Dict[str, BlockTree] = None


	def populate(self: 'BlockTree', tags: Iterable[Iterable[str]]) :
		for tag_set in tags :
			tree: BlockTree = self

			for tag in tag_set :
				match = True

				if tag.startswith('-') :
					match = False
					tag = tag[1:]

				if match :
					if not tree.match :
						tree.match = { }

					tree = tree.match

				else :
					if not tree.nomatch :
						tree.nomatch = { }

					tree = tree.nomatch

				if tag not in tree :
					tree[tag] = BlockTree()

				tree = tree[tag]


	def blocked(self: 'BlockTree', tags: Iterable[str]) -> bool :
		if not self.match and not self.nomatch :
			return False

		self.tags = set(tags)
		return self._blocked(self)


	def _blocked(self: 'BlockTree', tree: 'BlockTree') -> bool :
		# TODO: it really feels like there's a better way to do this check
		if not tree.match and not tree.nomatch :
			return True

		# eliminate as many keys immediately as possible, then iterate over them
		if tree.match :
			for key in tree.match.keys() & self.tags :
				if self._blocked(tree.match[key]) :
					return True

		if tree.nomatch :
			for key in tree.nomatch.keys() - self.tags :
				if self._blocked(tree.nomatch[key]) :
					return True

		return False


class InternalUser(BaseModel) :
	_post_id_converter = validator('icon', 'banner', pre=True, always=True, allow_reuse=True)(_post_id_converter)

	user_id: int
	name: str
	handle: str
	privacy: UserPrivacy
	icon: Optional[PostId]
	banner: Optional[PostId]
	website: Optional[str]
	created: datetime
	description: Optional[str]
	verified: Optional[Verified]
	badges: List[Badge]

	async def _following(self: 'InternalUser', user: KhUser) -> bool :
		follow_task: Task[bool] = ensure_future(DB.following(user.user_id, self.user_id))

		if not await user.authenticated(raise_error=False) :
			return None

		return await follow_task

	async def user(self: 'InternalUser', user: Optional[KhUser] = None) -> User :
		following: Optional[bool] = None

		if user :
			following = await self._following(user)

		return User(
			name = self.name,
			handle = self.handle,
			privacy = self.privacy,
			icon = self.icon,
			banner = self.banner,
			website = self.website,
			created = self.created,
			description = self.description,
			verified = self.verified,
			following = following,
			badges = self.badges,
		)

	async def portable(self: 'InternalUser', user: Optional[KhUser] = None) -> UserPortable :
		following: Optional[bool] = None

		if user :
			following = await self._following(user)

		return UserPortable(
			name = self.name,
			handle = self.handle,
			privacy = self.privacy,
			icon = self.icon,
			verified = self.verified,
			following = following,
		)


# this has to be defined here because of the response model
_InternalClient._user: Gateway = Gateway(UserHost + '/i1/user/{user_id}', InternalUser, method='GET')


@ArgsCache(30)
async def fetch_block_tree(client: _InternalClient, user: KhUser) -> Tuple[BlockTree, UserConfig] :
	tree: BlockTree = BlockTree()

	if not user.token :
		return tree

	# TODO: return underlying UserConfig here, once internal tokens are implemented
	user_config: UserConfig = await client.user_config(user.user_id)
	tree.populate(user_config.blocked_tags or [])
	return tree, user_config


async def is_post_blocked(client: _InternalClient, user: KhUser, uploader: str, uploader_id: int, tags: Iterable[str]) -> bool :
	block_tree, user_config = await fetch_block_tree(client, user)

	if uploader_id in user_config.blocked_users :
		return True

	tags: Set[str] = set(tags)
	tags.add('@' + uploader)  # TODO: user ids need to be added here instead of just handle, once changeable handles are added

	return block_tree.blocked(tags)


class InternalPost(BaseModel) :
	post_id: int
	title: Optional[str]
	description: Optional[str]
	user_id: int
	rating: Rating
	parent: Optional[int]
	privacy: Privacy
	created: Optional[datetime]
	updated: Optional[datetime]
	filename: Optional[str]
	media_type: Optional[MediaType]
	size: Optional[PostSize]


	async def user_portable(self: 'InternalPost', client: _InternalClient, user: KhUser) -> UserPortable :
		iuser: InternalUser = await client.user(self.user_id)
		return await iuser.portable(user)


	async def post(self: 'InternalPost', client: _InternalClient, user: KhUser) -> Post :
		post_id: PostId = PostId(self.post_id)
		uploader_task: Task[UserPortable] = ensure_future(self.user_portable(user))
		tags: TagGroups = ensure_future(client.post_tags(post_id))
		score: Task[Score] = ensure_future(DB.getScore(user, post_id))
		uploader: UserPortable = await uploader_task
		blocked: bool = await is_post_blocked(client, user, uploader.handle, self.user_id, await tags)

		return Post(
			post_id=post_id,
			title=self.title,
			description=self.description,
			user=uploader,
			score=await score,
			rating=self.rating,
			parent=self.parent,
			privacy=self.privacy,
			created=self.created,
			updated=self.updated,
			filename=self.filename,
			media_type=self.media_type,
			size=self.size,
			blocked=blocked,
		)


	async def authorized(self: 'InternalPost', client: _InternalClient, user: KhUser) -> bool :
		"""
		Checks if the given user is able to view this post. Follows the given rules:

		- is the post public or unlisted
		- is the user the uploader
		- TODO
			- if private, has the user been given explicit permission
			- if user is private, does the user follow the uploader

		:param client: client used to retrieve user details
		:param user: the user to check post availablility against
		:return: boolean - True if the user has permission, otherwise False
		"""

		if self.privacy in { Privacy.public, Privacy.unlisted } :
			return True

		if user.user_id == self.user_id :
			return True

		# use client to fetch the user and any other associated info to determine other methods of being authorized

		return False


# this has to be defined here because of the response model
_InternalClient._post: Gateway = Gateway(PostHost + '/i1/post/{post_id}', InternalPost, method='GET')
_InternalClient._user_posts: Gateway = Gateway(PostHost + '/i1/user/{user_id}', List[InternalPost], method='POST')


class InternalTag(BaseModel) :
	name: str
	owner: Optional[int]
	group: TagGroupPortable
	deprecated: bool
	inherited_tags: List[str]
	description: Optional[str]


	async def user_portable(self: 'InternalTag', client: _InternalClient, user: KhUser) -> Optional[UserPortable] :
		if not self.owner :
			return None

		iuser: InternalUser = await client.user(self.owner)
		return await iuser.portable(user)


	async def tag(self: 'InternalTag', client: _InternalClient, user: KhUser) -> Tag :
		owner: Task[UserPortable] = ensure_future(self.user_portable(client, user))
		tag_count: Task[int] = ensure_future(DB.tagCount(self.name))

		return Tag(
			tag=self.name,
			owner=await owner,
			group=self.group,
			deprecated=self.deprecated,
			inherited_tags=self.inherited_tags,
			description=self.description,
			count=await tag_count,
		)


# this has to be defined here because of the response model
_InternalClient._tag: Gateway = Gateway(TagHost + '/i1/tag/{tag}', InternalTag, method='GET')
