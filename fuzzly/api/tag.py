from kh_common.gateway import Gateway

from ..constants import TagHost
from ..models.tag import Tag, TagGroups


# Usage: FetchTag(tag='tag')
FetchTag: Gateway = Gateway(TagHost + '/v1/tag/{tag}', Tag, method='GET')

# Usage: FetchPostTags(post_id='abcd1234')
FetchPostTags: Gateway = Gateway(TagHost + '/v1/tags/{post_id}', TagGroups, method='GET')
