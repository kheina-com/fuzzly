from asyncio import Task, ensure_future
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from kh_common.auth import KhUser
from kh_common.caching import AerospikeCache
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.exceptions.http_error import NotFound
from kh_common.sql import SqlInterface
from pydantic import BaseModel, validator

from ._shared import Badge, PostId, User, UserPortable, UserPrivacy, Verified, _post_id_converter
from .post import PostId, Score


FollowKVS: KeyValueStore = KeyValueStore('kheina', 'following')
ScoreCache: KeyValueStore = KeyValueStore('kheina', 'score')
VoteCache: KeyValueStore = KeyValueStore('kheina', 'votes')
CountKVS: KeyValueStore = KeyValueStore('kheina', 'tag_count',  local_TTL=60)
UserKVS: KeyValueStore = KeyValueStore('kheina', 'users', local_TTL=60)


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

	_following: Callable[['InternalUser', KhUser], Coroutine[Any, Any, bool]]

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


class InternalScore(BaseModel) :
	up: int
	down: int
	total: int


# this steals the idea of a map from kh_common.map.Map, probably use that when types are figured out in a generic way
class BadgeMap(SqlInterface, dict) :

	def __missing__(self, key: int) -> Badge :
		data: Tuple[str, str] = self.query(f"""
			SELECT emoji, label
			FROM kheina.public.badges
			WHERE badge_id = %s
			LIMIT 1;
			""",
			(key,),
			fetch_one=True,
		)
		self[key] = Badge(emoji=data[0], label=data[1])
		return self[key]

badge_map: BadgeMap = BadgeMap()


# this steals the idea of a map from kh_common.map.Map, probably use that when types are figured out in a generic way
class PrivacyMap(SqlInterface, dict) :

	def __missing__(self, key: int) -> UserPrivacy :
		data: Tuple[str] = self.query(f"""
			SELECT type
			FROM kheina.public.privacy
			WHERE privacy_id = %s
			LIMIT 1;
			""",
			(key,),
			fetch_one=True,
		)
		self[key] = UserPrivacy(value=data[0])
		return self[key]

privacy_map: PrivacyMap = PrivacyMap()


class DBI(SqlInterface) :

	@AerospikeCache('kheina', 'following', '{user_id}|{target}', _kvs=FollowKVS)
	async def following(self, user_id: int, target: int) -> bool :
		"""
		returns true if the user specified by user_id is following the user specified by target
		"""

		data = await self.query_async("""
			SELECT count(1)
			FROM kheina.public.following
			WHERE following.user_id = %s
				AND following.follows = %s;
			""",
			(user_id, target),
			fetch_all=True,
		)

		if not data :
			return False

		return bool(data[0])


	async def following_many(self, user_id: int, targets: List[int]) -> Dict[int, bool] :
		"""
		returns a map of target user id -> following bool
		"""

		data: List[Tuple[int, int]] = await self.query_async("""
			SELECT following.follows, count(1)
			FROM kheina.public.following
			WHERE following.user_id = %s
				AND following.follows = any(%s)
			GROUP BY following.follows;
			""",
			(user_id, targets),
			fetch_all=True,
		)

		return_value: Dict[int, bool] = {
			target: False
			for target in targets
		}

		for target, following in data :
			following: bool = bool(following)
			return_value[target] = following
			ensure_future(FollowKVS.put_async(f'{user_id}|{target}', following))

		return return_value


	@AerospikeCache('kheina', 'score', '{post_id}', _kvs=ScoreCache)
	async def _get_score(self, post_id: PostId) -> Optional[InternalScore] :
		data: List[int] = await self.query_async("""
			SELECT
				post_scores.upvotes,
				post_scores.downvotes
			FROM kheina.public.post_scores
			WHERE post_scores.post_id = %s;
			""",
			(post_id.int(),),
			fetch_one=True,
		)

		if not data :
			return None

		return InternalScore(
			up=data[0],
			down=data[1],
			total=sum(data),
		)


	async def scores_many(self, post_ids: List[PostId]) -> Dict[PostId, Optional[InternalScore]] :
		scores: Dict[PostId, Optional[InternalScore]] = {
			post_id: None
			for post_id in post_ids
		}

		data: List[Tuple(int, int, int)] = await self.query_async("""
			SELECT
				post_scores.post_id,
				post_scores.upvotes,
				post_scores.downvotes
			FROM kheina.public.post_scores
			WHERE post_scores.post_id = any(%s);
			""",
			(list(map(int, post_ids)),),
			fetch_all=True,
		)

		if not data :
			return scores

		for post_id, up, down in data :
			post_id: PostId = PostId(post_id)
			score: InternalScore = InternalScore(
				up=up,
				down=down,
				total=up + down,
			)
			scores[post_id] = score
			ensure_future(ScoreCache.put_async(post_id, score))

		return scores


	@AerospikeCache('kheina', 'votes', '{user_id}|{post_id}', _kvs=VoteCache)
	async def _get_vote(self, user_id: int, post_id: PostId) -> int :
		data: Optional[Tuple[bool]] = await self.query_async("""
			SELECT
				upvote
			FROM kheina.public.post_votes
			WHERE post_votes.user_id = %s
				AND post_votes.post_id = %s;
			""",
			(user_id, post_id.int()),
			fetch_one=True,
		)

		if not data :
			return 0

		return 1 if data[0] else -1


	async def votes_many(self, user_id: int, post_ids: List[PostId]) -> Dict[PostId, int] :
		votes: Dict[PostId, int] = {
			post_id: 0
			for post_id in post_ids
		}
		data: List[Tuple[int, int]] = await self.query_async("""
			SELECT
				post_votes.post_id,
				post_votes.upvote
			FROM kheina.public.post_votes
			WHERE post_votes.user_id = %s
				AND post_votes.post_id = any(%s);
			""",
			(user_id, list(map(int, post_ids))),
			fetch_all=True,
		)

		if not data :
			return votes

		for post_id, upvote in data :
			post_id: PostId = PostId(post_id)
			vote: int = 1 if upvote else -1
			votes[post_id] = vote
			ensure_future(VoteCache.put_async(f'{user_id}|{post_id}', vote))

		return votes


	async def getScore(self, user: KhUser, post_id: PostId) -> Optional[Score] :
		score: Task[Optional[InternalScore]] = ensure_future(self._get_score(post_id))
		vote: Task[int] = ensure_future(self._get_vote(user.user_id, post_id))

		score: Optional[InternalScore] = await score

		if not score :
			return None

		return Score(
			up=score.up,
			down=score.down,
			total=score.total,
			user_vote=await vote,
		)


	@AerospikeCache('kheina', 'tag_count', '{tag}', _kvs=CountKVS)
	async def tagCount(self, tag: str) -> int :
		data = await self.query_async("""
			SELECT COUNT(1)
			FROM kheina.public.tags
				INNER JOIN kheina.public.tag_post
					ON tags.tag_id = tag_post.tag_id
				INNER JOIN kheina.public.posts
					ON tag_post.post_id = posts.post_id
						AND posts.privacy_id = privacy_to_id('public')
			WHERE tags.tag = %s;
			""",
			(tag,),
			fetch_one=True,
		)

		if not data :
			return 0

		return data[0]


	async def tags_many(self, post_ids: List[PostId]) -> Dict[PostId, List[str]] :
		# TODO: it may be worth doing a more complex query here for the tag classes
		# so that the response data can be cached for future use
		tags: Dict[PostId, List[str]] = {
			post_id: []
			for post_id in post_ids
		}
		data: List[Tuple[int, List[str]]] = await self.query_async("""
			SELECT tag_post.post_id, array_agg(tags.tag)
			FROM kheina.public.tag_post
				INNER JOIN kheina.public.tags
					ON tags.tag_id = tag_post.tag_id
						AND tags.deprecated = false
			WHERE tag_post.post_id = any(%s)
			GROUP BY tag_post.post_id;
			""",
			(list(map(int, post_ids)),),
			fetch_all=True,
		)

		for post_id, tag_list in data :
			tags[PostId(post_id)] = list(filter(None, tag_list))

		return tags


	async def _handle_to_user_id(self, handle: str) -> int :
		data = await self.query_async("""
			SELECT
				users.user_id
			FROM kheina.public.users
			WHERE lower(users.handle) = lower(%s);
			""",
			(handle.lower(),),
			fetch_one=True,
		)

		if not data :
			raise NotFound('no data was found for the provided user.')

		return data[0]


	async def users_many(self, user_ids: List[int]) -> Dict[int, InternalUser] :

		data: List[tuple] = await self.query_async("""
			SELECT
				users.user_id,
				users.display_name,
				users.handle,
				users.privacy_id,
				users.icon,
				users.website,
				users.created_on,
				users.description,
				users.banner,
				users.admin,
				users.mod,
				users.verified,
				array_agg(user_badge.badge_id)
			FROM kheina.public.users
				LEFT JOIN kheina.public.user_badge
					ON user_badge.user_id = users.user_id
			WHERE users.user_id = any(%s)
			GROUP BY
				users.user_id;
			""",
			(user_ids,),
			fetch_all=True,
		)

		if not data :
			return { }

		users: Dict[int, InternalUser] = { }
		for datum in data :
			verified: Optional[Verified] = None

			if datum[9] :
				verified = Verified.admin

			elif datum[10] :
				verified = Verified.mod

			elif datum[11] :
				verified = Verified.artist

			user: InternalUser = InternalUser(
				user_id = datum[0],
				name = datum[1],
				handle = datum[2],
				privacy = privacy_map[datum[3]],
				icon = datum[4],
				website = datum[5],
				created = datum[6],
				description = datum[7],
				banner = datum[8],
				verified = verified,
				badges = list(map(badge_map.__getitem__, filter(None, datum[12]))),
			)
			users[datum[0]] = user
			ensure_future(UserKVS.put_async(str(datum[0]), user))

		return users
