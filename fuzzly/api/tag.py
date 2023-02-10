from kh_common.gateway import Gateway

from fuzzly.constants import TagHost
from fuzzly.models.tag import Tag, TagGroups


FetchTag: Gateway = Gateway(TagHost + '/v1/tag/{tag}', Tag, method='GET')
FetchPostTags: Gateway = Gateway(TagHost + '/v1/post/{post_id}', TagGroups, method='GET')
