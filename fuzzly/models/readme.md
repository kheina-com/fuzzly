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
from fuzzly.models.post import InternalPost, Post
from fuzzly.models.user import InternalUser, User

ipost: InternalPost
iuser: InternalUser

kh_user: KhUser  # this is an object available within endpoints themselves and represents the user calling the endpoint

post: Post = await ipost.post(kh_user)
user: User = await iuser.post(kh_user)
```
