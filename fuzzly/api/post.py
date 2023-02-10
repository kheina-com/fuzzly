from kh_common.gateway import Gateway

from ..constants import PostHost
from ..models.post import Post


# Usage: FetchPost(post_id='abcd1234')
FetchPost: Gateway = Gateway(PostHost + '/v1/post/{post_id}', Post, method='GET')

# Usage: FetchMyPosts({ 'sort': 'new', 'count': 64, 'page': 1 })
FetchMyPosts: Gateway = Gateway(PostHost + '/v1/my_posts', Post, method='POST')
