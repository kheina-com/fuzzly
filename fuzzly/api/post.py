from kh_common.gateway import Gateway

from fuzzly.constants import PostHost
from fuzzly.models.post import Post


# Usage: FetchPost(post_id='abcd1234')
FetchPost: Gateway = Gateway(PostHost + '/v1/post/{post_id}', Post, method='GET')

# Usage: FetchMyPosts({ 'sort': 'new', 'count': 64, 'page': 1 })
FetchMyPosts: Gateway = Gateway(PostHost + '/v1/my_posts', Post, method='POST')

# this requires more thinking to get working
# self._kvs = KeyValueStore('kheina', 'posts')
# self._post = AerospikeCache('kheina', 'posts', '{post_id}', read_only=True, _kvs=self._kvs)(self.authenticated(Gateway(Host + '/i1/post/{post_id}', InternalPost, method='GET')))
