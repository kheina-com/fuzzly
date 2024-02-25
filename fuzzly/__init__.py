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
	"""
	Notice that all client functions are `async`. This is because http requests are made under the hood and they are done in parallel with other requests.
	"""

	################################################## POST ##################################################

	@Client.authenticated
	async def post(self: Client, post_id: PostId, auth: str = None) -> Post :
		"""
		Retrieves the post indicated by the provided `post_id`.
		```python
		client: FuzzlyClient
		await client.post('Lw_KpQM6')
		```
		"""
		return await FetchPost(post_id=post_id, auth=auth)


	@Client.authenticated
	async def my_posts(self: Client, sort: PostSort = PostSort.new, count: int = 64, page: int = 1, auth: str = None) -> List[Post] :
		"""
		Retrieves the user's own posts. Requires a bot token to be provided to the client.
		```python
		client: FuzzlyClient
		await client.my_posts()
		```
		"""
		return await FetchMyPosts({ 'sort': sort.name, 'count': count, 'page': page }, auth=auth)


	################################################## TAGS ##################################################

	@Client.authenticated
	async def tag(self: Client, tag: str, auth: str = None) -> Tag :
		"""
		Retrieves the tag specified by the provided `tag`.
		```python
		client: FuzzlyClient
		await client.tag('female')
		```
		"""
		return await FetchTag(tag=tag, auth=auth)


	@Client.authenticated
	async def post_tags(self: Client, post_id: PostId, auth: str = None) -> TagGroups :
		"""
		Retrieves the tags belonging to a post, specified by the provided `post_id`.
		```python
		client: FuzzlyClient
		await client.post_tags('Lw_KpQM6')
		```
		"""
		return await FetchPostTags(post_id=post_id, auth=auth)


	################################################## SETS ##################################################

	@Client.authenticated
	async def set(self: Client, set_id: SetId, auth: str = None) -> Set :
		"""
		Retrieves the set indicated by the provided `set_id`.
		```python
		client: FuzzlyClient
		await client.set('abc-123')
		```
		"""
		return await FetchSet(set_id=set_id, auth=auth)


	@Client.authenticated
	async def user_sets(self: Client, handle: str, auth: str = None) -> List[Set] :
		"""
		Retrieves the sets owned by the user indicated by the provided `handle`.
		```python
		client: FuzzlyClient
		await client.user_sets('handle')
		```
		"""
		return await FetchUserSets(handle=handle, auth=auth)


	@Client.authenticated
	async def post_sets(self: Client, post_id: PostId, auth: str = None) -> List[PostSet] :
		"""
		Retrieves all sets that contain the post indicated by the provided `post_id`.

		NOTE: the return model also contains the post's neighbors within the set
		```python
		client: FuzzlyClient
		await client.post_sets('abcd1234')
		```
		"""
		return await FetchPostSets(post_id=post_id, auth=auth)
