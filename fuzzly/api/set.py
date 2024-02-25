from typing import List

from kh_common.gateway import Gateway

from ..constants import SetHost
from ..models.set import PostSet, Set


# Usage: FetchSet(set_id='abcd123')
FetchSet = Gateway(SetHost + '/v1/set/{set_id}', Set, method='GET')


# Usage: FetchUserSets(handle='@handle')
FetchUserSets = Gateway(SetHost + '/v1/user/{handle}', List[Set], method='GET')


# Usage: FetchPostSets(post_id='abcd1234')
FetchPostSets = Gateway(SetHost + '/v1/post/{post_id}', List[PostSet], method='GET')
