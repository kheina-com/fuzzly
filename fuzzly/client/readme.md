## Client
Defines a fuzz.ly client that can accept a bot token and self-manage authentication


## Usage
Initialize your client with or without a client token provided by the account service

```python
from fuzzly.client import Client

# token received from https://account.fuzz.ly/v1/bot_create
token: str = 'aGV5IG1hbi4gaXQncyB3ZWlyZCB0aGF0IHlvdSBsb29rZWQgYXQgdGhpcywgYnV0IHRoaXMgaXNuJ3QgYSByZWFsIHRva2Vu'
fuzzly_client: Client = Client(token)

# or, to retrieve only publicly available data, omit token
fuzzly_client: Client = Client()
```

To inject credentials into functions, inherit the `Client` class and create member functions that contain the `auth` keyword argument

```python
from fuzzly.constants import PostHost
from fuzzly.models.post import Post
from fuzzly.client import Client

class MyClient(Client) :
	@Client.authenticated  # notice that this is @Client.authenticated and not @MyClient or @self
	async def post(self, post_id: str, auth: str = None) :
		# auth is a str object containing a valid fuzz.ly authorization bearer token
		async with aiohttp.request(
			'GET',
			PostHost + f'/v1/post/{post_id}',
			headers = { 'authorization': 'Bearer ' + auth },
			timeout = aiohttp.ClientTimeout(30),
			raise_for_status = True,
		) as response :
			return await response.json()

fuzzly_client: MyClient = MyClient(token)
post: dict = await fuzzly_client.post('abcd1234')  # credentials are automatically injected
```
