## Models
Defines all fuzz.ly models needed for interaction with any of the fuzz.ly APIs, including internal and external endpoints.

Models are traditionally named with PascalCase and can be imported from individual files within the models folder.

Internal models (those returned by internal endpoints defined by `i\d` versus `v\d`) have the `Internal` prefix

## Usage
```python
from fuzzly.models.post import MediaType, Post, PostId, PostSize, PostSort, Score, Privacy, Rating
from fuzzly.models.user import Badge, User, Privacy, Verified
```

Internal models can traditionally be converted to their external counterparts by running the attached async function named after the model
```python
from fuzzly.api.internal import InternalClient
from fuzzly.models.internal import InternalPost, InternalUser, InternalTag
from fuzzly.models.post import Post
from fuzzly.models.user import User
from fuzzly.models.tag import Tag

ipost: InternalPost
iuser: InternalUser
itag: InternalTag

kh_user: KhUser  # this is an object available within endpoints themselves and represents the user calling the endpoint
client: InternalClient  # an internal client instance is required so that auth can be passed to further internal api calls

post: Post = await ipost.post(client, kh_user)
user: User = await iuser.user(client, kh_user)
tag: Tag = await itag.tag(client, kh_user)

# when needing to populate many internal posts use an InternalPosts object
from fuzzly.models.internal import InternalPosts

iposts: InternalPosts = InternalPosts()
iposts.append(ipost)
# or you can pass in a post list directly
iposts = InternalPosts(post_list=[ipost])

posts: List[Post] = await iposts.posts(client, kh_user)
```
