from asyncio import Task, ensure_future
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Iterable, List, Optional
from typing import Set as SetType
from typing import Tuple

from kh_common.auth import KhUser, Scope
from kh_common.base64 import b64decode, b64encode
from kh_common.caching import AerospikeCache, ArgsCache
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.gateway import Gateway
from kh_common.utilities import flatten
from pydantic import BaseModel, validator

from ..client import Client
from ..constants import ConfigHost, PostHost, SetHost, TagHost, UserHost
from ._database import DBI, FollowKVS, InternalScore, InternalUser, ScoreCache, UserKVS, VoteCache
from ._shared import PostId, PostSize, SetId, UserPortable, UserPrivacy, _post_id_converter
from .config import UserConfig
from .post import MediaType, Post, PostId, PostSize, PostSort, Privacy, Rating, Score
from .set import Set
from .tag import Tag, TagGroupPortable, TagGroups
from .user import UserPortable


# each internal endpoint will have it's own exported kvs so that they can be overwritten or imported by users
UserConfigKVS: KeyValueStore = KeyValueStore('kheina', 'configs')
TagKVS: KeyValueStore = KeyValueStore('kheina', 'tags')
PostKVS: KeyValueStore = KeyValueStore('kheina', 'posts')
SetKVS: KeyValueStore = KeyValueStore('kheina', 'sets')

# internal functions sometimes need to interact with the db, this is done through this interface
DB: DBI = DBI()


class _InternalClient(Client) :
	"""
	There's a lot of api calls that needs to occur within internal models to work correctly.
	Those are set up within this client so that the main client in the root does not break without internal auth/kvs access
	"""

	_user_config: Gateway = Gateway(ConfigHost + '/i1/user/{user_id}', UserConfig, method='GET')
	_post_tags: Gateway = Gateway(TagHost + '/i1/tags/{post_id}', TagGroups, method='GET')
	_user_posts: Gateway  # this will be assigned later
	_post: Gateway  # this will be assigned later
	_user: Gateway  # this will be assigned later
	_tag: Gateway  # this will be assigned later
	_set: Gateway  # this will be assigned later

	following_many: Callable[[KhUser, List[int]], Coroutine[Any, Any, Dict[int, bool]]]
	users_many: Callable[[List[int]], Coroutine[Any, Any, Dict[int, InternalUser]]]

	votes_many: Callable[[KhUser, List[PostId]], Coroutine[Any, Any, Dict[PostId, int]]]
	scores_many: Callable[[List[PostId]], Coroutine[Any, Any, Dict[PostId, Optional[InternalScore]]]]

	tags_many: Callable[[List[PostId]], Coroutine[Any, Any, Dict[PostId, List[str]]]]


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


	@AerospikeCache('kheina', 'sets', '{set_id}', read_only=True, _kvs=SetKVS)
	@Client.authenticated
	async def set(self: Client, set_id: SetId, auth: str = None) -> 'InternalSet' :
		return await _InternalClient._set(set_id=set_id, auth=auth)


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
		self.tags: SetType[str] = None
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


# this has to be defined here because the type needs to be used in DBI
async def _following(self: 'InternalUser', user: KhUser) -> bool :
	follow_task: Task[bool] = ensure_future(DB.following(user.user_id, self.user_id))

	if not await user.authenticated(raise_error=False) :
		return None

	return await follow_task

InternalUser._following = _following


# this has to be defined here because of the response model
_InternalClient._user: Gateway = Gateway(UserHost + '/i1/user/{user_id}', InternalUser, method='GET')


@ArgsCache(30)
async def fetch_block_tree(client: _InternalClient, user: KhUser) -> Tuple[BlockTree, UserConfig] :
	tree: BlockTree = BlockTree()

	if not user.token :
		# TODO: create and return a default config
		return tree, UserConfig()

	# TODO: return underlying UserConfig here, once internal tokens are implemented
	user_config: UserConfig = await client.user_config(user.user_id)
	tree.populate(user_config.blocked_tags or [])
	return tree, user_config


async def is_post_blocked(client: _InternalClient, user: KhUser, uploader: str, uploader_id: int, tags: Iterable[str]) -> bool :
	block_tree, user_config = await fetch_block_tree(client, user)

	if user_config.blocked_users and uploader_id in user_config.blocked_users :
		return True

	tags: SetType[str] = set(tags)
	tags.add('@' + uploader)  # TODO: user ids need to be added here instead of just handle, once changeable handles are added

	return block_tree.blocked(tags)

def _thumbhash_converter(value: Any) -> Optional[bytes] :
	if not value or isinstance(value, bytes):
		return value

	if isinstance(value, str) :
		return b64decode(value)

	return bytes(value)


class InternalPost(BaseModel) :
	_thumbhash_converter = validator('thumbhash', pre=True, always=True, allow_reuse=True)(_thumbhash_converter)

	class Config:
		json_encoders = {
			bytes: lambda x: b64encode(x).decode(),
		}

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
	thumbhash: Optional[bytes]


	async def user_portable(self: 'InternalPost', client: _InternalClient, user: KhUser) -> UserPortable :
		iuser: InternalUser = await client.user(self.user_id)
		return await iuser.portable(user)


	async def post(self: 'InternalPost', client: _InternalClient, user: KhUser) -> Post :
		post_id: PostId = PostId(self.post_id)
		uploader_task: Task[UserPortable] = ensure_future(self.user_portable(client, user))
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
			thumbhash=self.thumbhash,
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

		if not await user.authenticated(raise_error=False) :
			return False

		if user.user_id == self.user_id :
			return True

		if await user.verify_scope(Scope.mod, raise_error=False) :
			return True

		# use client to fetch the user and any other associated info to determine other methods of being authorized

		return False


# this has to be defined here because of the response model
_InternalClient._post: Gateway = Gateway(PostHost + '/i1/post/{post_id}', InternalPost, method='GET')
_InternalClient._user_posts: Gateway = Gateway(PostHost + '/i1/user/{user_id}', List[InternalPost], method='POST')

async def following_many(self: _InternalClient, user: KhUser, targets: List[int]) -> Dict[int, bool] :
	"""
	returns a dictionary of target user id -> bool indicating if user follows target
	"""
	following_map: Dict[str, int] = dict(map(lambda x : (f'{user.user_id}|{x}', x), targets))
	following: Dict[int, Optional[bool]] = {
		# remember we need to convert the dict key from the string needed for aerospike back to an int
		following_map[key]: following
		for key, following in
		(await FollowKVS.get_many_async(following_map.keys())).items()
	}

	sql_user_ids: List[int] = [target for target, f in following.items() if f is None]

	if sql_user_ids :
		following.update(await DB.following_many(user.user_id, sql_user_ids))

	return following

_InternalClient.following_many = following_many


async def users_many(self: _InternalClient, user_ids: List[int]) -> Dict[int, InternalUser] :
	"""
	returns a dictionary of user_id -> populated User objects
	"""
	users: Dict[int, Optional[InternalUser]] = {
		int(user_id): iuser
		for user_id, iuser in 
		(await UserKVS.get_many_async(list(map(str, user_ids)))).items()
	}

	sql_user_ids: List[int] = [user_id for user_id, user in users.items() if user is None or type(user) == bytearray]

	if sql_user_ids :
		users.update(await DB.users_many(sql_user_ids))

	return users

_InternalClient.users_many = users_many


async def votes_many(self: _InternalClient, user: KhUser, post_ids: List[PostId]) -> Dict[PostId, int] :
	votes_map: Dict[str, PostId] = dict(map(lambda x : (f'{user.user_id}|{x}', x), post_ids))
	votes: Dict[PostId, Optional[int]] = {
		votes_map[key]: vote
		for key, vote in
		(await VoteCache.get_many_async(votes_map.keys())).items()
	}

	sql_post_ids: List[PostId] = [PostId(post_id) for post_id, vote in votes.items() if vote is None]

	if sql_post_ids :
		votes.update(await DB.votes_many(user.user_id, sql_post_ids))

	return votes

_InternalClient.votes_many = votes_many


async def scores_many(self: _InternalClient, post_ids: List[PostId]) -> Dict[PostId, Optional[InternalScore]] :
	scores: Dict[PostId, Optional[InternalScore]] = await ScoreCache.get_many_async(post_ids)

	sql_post_ids: List[PostId] = [PostId(post_id) for post_id, score in scores.items() if score is None or type(score) == bytearray]

	if sql_post_ids :
		scores.update(await DB.scores_many(sql_post_ids))

	return scores

_InternalClient.scores_many = scores_many


async def tags_many(self: _InternalClient, post_ids: List[PostId]) -> Dict[PostId, List[str]] :
	tags: Dict[PostId, Optional[List[str]]] = {
		post_id: flatten(tag_groups) if tag_groups and type(tag_groups) != bytearray else None
		for post_id, tag_groups in
		(await TagKVS.get_many_async(post_ids)).items()
	}

	sql_post_ids: List[PostId] = [PostId(post_id) for post_id, tag_list in tags.items() if tag_list is None]

	if sql_post_ids :
		tags.update(await DB.tags_many(sql_post_ids))

	return tags

_InternalClient.tags_many = tags_many


class InternalPosts(BaseModel) :
	post_list: List[InternalPost] = []

	def append(self: 'InternalPosts', post: InternalPost) :
		return self.post_list.append(post)


	async def uploaders(self: 'InternalPosts', client: _InternalClient, user: KhUser) -> Dict[int, UserPortable] :
		"""
		returns populated user objects for every uploader id provided

		:return: dict in the form user id -> populated User object
		"""
		uploader_ids: List[int] = list(set(map(lambda x : x.user_id, self.post_list)))
		users_task: Task[Dict[int, InternalUser]] = ensure_future(client.users_many(uploader_ids))
		following: Dict[int, Optional[bool]]

		if await user.authenticated(False) :
			following = await client.following_many(user, uploader_ids)

		else :
			following = defaultdict(lambda : None)

		iusers: Dict[int, InternalUser] = await users_task

		return {
			user_id: UserPortable(
				name=iuser.name,
				handle=iuser.handle,
				privacy=iuser.privacy,
				icon=iuser.icon,
				verified=iuser.verified,
				following=following[user_id],
			)
			for user_id, iuser in iusers.items()
		}


	async def scores(self: 'InternalPosts', client: _InternalClient, user: KhUser) -> Dict[PostId, Optional[Score]] :
		"""
		returns populated score objects for every post id provided

		:return: dict in the form post id -> populated Score object
		"""
		scores: Dict[PostId, Optional[Score]] = { }
		post_ids: List[PostId] = []

		for post in self.post_list :
			post_id: PostId = PostId(post.post_id)

			# only grab posts that can actually have scores
			if post.privacy not in { Privacy.draft, Privacy.unpublished } :
				post_ids.append(post_id)

			# but put all of them in the dict
			scores[post_id] = None

		iscores_task: Task[Dict[PostId, Optional[InternalScore]]] = ensure_future(client.scores_many(post_ids))
		user_votes: Dict[PostId, int]

		if await user.authenticated(False) :
			user_votes = await client.votes_many(user, post_ids)

		else :
			user_votes = defaultdict(lambda : 0)

		iscores: Dict[PostId, Optional[InternalScore]] = await iscores_task

		for post_id, iscore in iscores.items() :
			# the score may still be None, technically
			if iscore :
				scores[post_id] = Score(
					up=iscore.up,
					down=iscore.down,
					total=iscore.total,
					user_vote=user_votes[post_id],
				)

		return scores


	async def posts(self: 'InternalPosts', client: _InternalClient, user: KhUser) -> List[Post] :
		"""
		returns a list of external post objects populated with user and other information
		"""

		uploaders_task: Task[Dict[int, UserPortable]] = ensure_future(self.uploaders(client, user))
		scores_task: Task[Dict[PostId, Optional[Score]]] = ensure_future(self.scores(client, user))

		tags: Dict[PostId, List[str]] = await client.tags_many(list(map(lambda x : PostId(x.post_id), self.post_list)))
		uploaders: Dict[int, UserPortable] = await uploaders_task
		scores: Dict[PostId, Optional[Score]] = await scores_task

		posts: List[Post] = []
		for post in self.post_list :
			post_id: PostId = PostId(post.post_id)
			posts.append(Post(
				post_id=post_id,
				title=post.title,
				description=post.description,
				user=uploaders[post.user_id],
				score=scores[post_id],
				rating=post.rating,
				parent=post.parent,
				privacy=post.privacy,
				created=post.created,
				updated=post.updated,
				filename=post.filename,
				media_type=post.media_type,
				size=post.size,
				# only the first call retrieves blocked info, all the rest should be cached and not actually await
				blocked=await is_post_blocked(client, user, uploaders[post.user_id].handle, post.user_id, tags[post_id]),
				thumbhash=post.thumbhash,
			))
		
		return posts


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
		owner: Task[Optional[UserPortable]] = ensure_future(self.user_portable(client, user))
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


class InternalSet(BaseModel) :
	_post_id_converter = validator('first', 'last', pre=True, always=True, allow_reuse=True)(_post_id_converter)

	set_id: int
	owner: int
	count: int
	title: Optional[str]
	description: Optional[str]
	privacy: UserPrivacy
	created: datetime
	updated: datetime
	first: Optional[PostId]
	last: Optional[PostId]


	async def user_portable(self: 'InternalSet', client: _InternalClient, user: KhUser) -> Optional[UserPortable] :
		iuser: InternalUser = await client.user(self.owner)
		return await iuser.portable(user)


	async def _post(self: 'InternalSet', client: _InternalClient, user: KhUser, post_id: Optional[PostId]) -> Optional[Post] :
		if not post_id :
			return None

		ipost: InternalPost = await client.post(post_id)

		if not ipost.authorized(client, user) :
			return None

		return await ipost.post(client, user)


	async def set(self: 'InternalSet', client: _InternalClient, user: KhUser) -> Set :
		owner: Task[Optional[UserPortable]] = ensure_future(self.user_portable(client, user))
		first: Task[Optional[Post]] = ensure_future(self._post(client, user, self.first))
		last: Task[Optional[Post]] = ensure_future(self._post(client, user, self.last))

		return Set(
			set_id=SetId(self.set_id),
			owner=await owner,
			count=self.count,
			title=self.title,
			description=self.description,
			privacy=self.privacy,
			created=self.created,
			updated=self.updated,
			first=await first,
			last=await last,
		)


	async def authorized(self: 'InternalSet', client: _InternalClient, user: KhUser) -> bool :
		"""
		Checks if the given user is able to view this set. Follows the given rules:

		- is the set public
		- is the user the owner
		- TODO:
			- if private, has the user been given explicit permission
			- if user is private, does the user follow the uploader

		:param client: client used to retrieve user details
		:param user: the user to check set availablility against
		:return: boolean - True if the user has permission, otherwise False
		"""

		if self.privacy == UserPrivacy.public :
			return True

		if not await user.authenticated(raise_error=False) :
			return False

		if user.user_id == self.owner :
			return True

		if await user.verify_scope(Scope.mod, raise_error=False) :
			return True

		# use client to fetch the user and any other associated info to determine other methods of being authorized

		return False

# this has to be defined here because of the response model
_InternalClient._set: Gateway = Gateway(SetHost + '/i1/set/{set_id}', InternalSet, method='GET')
