"""A python client library for fuzz.ly"""  # this comment should match the package slogan under the logo in the readme


__version__: str = '0.0.5'


from typing import List

from .api.post import FetchMyPosts, FetchPost
from .api.set import FetchPostSets, FetchSet, FetchUserSets
from .api.tag import FetchPostTags, FetchTag
from .client import Client
from .models.post import Post, PostId, PostSort
from .models.set import PostSet, Set, SetId
from .models.tag import Tag, TagGroups


class FuzzlyClient(Client) :

	################################################## POST ##################################################

	@Client.authenticated
	async def post(self: Client, post_id: PostId, auth: str = None) -> Post :
		return await FetchPost(post_id=post_id, auth=auth)


	@Client.authenticated
	async def my_posts(self: Client, sort: PostSort = PostSort.new, count: int = 64, page: int = 1, auth: str = None) -> List[Post] :
		return await FetchMyPosts({ 'sort': sort.name, 'count': count, 'page': page }, auth=auth)


	################################################## TAGS ##################################################

	@Client.authenticated
	async def tag(self: Client, tag: str, auth: str = None) -> Tag :
		return await FetchTag(tag=tag, auth=auth)


	@Client.authenticated
	async def post_tags(self: Client, post_id: PostId, auth: str = None) -> TagGroups :
		return await FetchPostTags(post_id=post_id, auth=auth)


	################################################## SETS ##################################################

	@Client.authenticated
	async def set(self: Client, set_id: SetId, auth: str = None) -> Set :
		return await FetchSet(set_id=set_id, auth=auth)


	@Client.authenticated
	async def user_sets(self: Client, handle: str, auth: str = None) -> List[Set] :
		return await FetchUserSets(handle=handle, auth=auth)


	@Client.authenticated
	async def post_sets(self: Client, post_id: PostId, auth: str = None) -> List[PostSet] :
		return await FetchPostSets(post_id=post_id, auth=auth)
