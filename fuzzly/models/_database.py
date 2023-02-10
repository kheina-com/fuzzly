from asyncio import Task, ensure_future
from typing import Dict, List, Optional

from kh_common.auth import KhUser
from kh_common.caching import AerospikeCache
from kh_common.caching.key_value_store import KeyValueStore
from kh_common.exceptions.http_error import NotFound
from kh_common.sql import SqlInterface
from pydantic import BaseModel

from .post import PostId, Score


FollowKVS: KeyValueStore = KeyValueStore('kheina', 'following')
ScoreCache: KeyValueStore = KeyValueStore('kheina', 'score')
VoteCache: KeyValueStore = KeyValueStore('kheina', 'votes')
CountKVS: KeyValueStore = KeyValueStore('kheina', 'tag_count',  local_TTL=60)


class InternalScore(BaseModel) :
	up: int
	down: int
	total: int


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


	@AerospikeCache('kheina', 'score', '{post_id}', _kvs=ScoreCache)
	async def _get_score(self, post_id: PostId) -> Optional[InternalScore] :
		data: List[int] = await self.query_async("""
			SELECT
				post_scores.upvotes,
				post_scores.downvotes
			FROM kheina.public.post_scores
			WHERE post_scores.post_id = %s
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


	@AerospikeCache('kheina', 'votes', '{user}.{post_id}', _kvs=VoteCache)
	async def _get_vote(self, user_id: int, post_id: PostId) -> int :
		data: List[int] = await self.query_async("""
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


	@AerospikeCache('kheina', 'votes', '{tag}', _kvs=CountKVS)
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
