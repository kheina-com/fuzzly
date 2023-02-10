"""A python client library for fuzz.ly""" # this comment should match the package slogan under the logo in the readme


__version__: str = '0.0.1'


from typing import List

from .api.post import FetchMyPosts, FetchPost
from .client import Client
from .models.post import Post, PostId, PostSort


class FuzzlyClient(Client) :

	@Client.authenticated
	async def post(self: Client, post_id: PostId, auth: str = None) -> Post :
		return await FetchPost(post_id=post_id, auth=auth)


	@Client.authenticated
	async def my_posts(self: Client, sort: PostSort = PostSort.new, count: int = 64, page: int = 1, auth: str = None) -> List[Post] :
		return await FetchMyPosts({ 'sort': sort.name, 'count': count, 'page': page }, auth=auth)
