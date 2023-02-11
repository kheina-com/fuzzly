from asyncio import Task, ensure_future
from inspect import Parameter, iscoroutinefunction, isfunction, signature
from time import time
from typing import Any, Callable, Dict, Optional, Tuple

from aiohttp import ClientResponseError
from kh_common.exceptions import http_error
from kh_common.gateway import Gateway

from ..constants import AccountHost
from ..models.auth import LoginResponse


class Client :
	"""
	Defines a fuzz.ly client that can accept a bot token and self-manage authentication
	"""

	def __init__(self: 'Client', token: Optional[str] = None) :
		"""
		Initializes the internal bot credentials and auth token. should only be called once on application startup.

		:param token: base64 encoded bot login token generated from the fuzz.ly bot creation endpoint
		"""
		self.initialize(token)
		
		# register all of the http errors in common repo so we can wrap aiohttp.ClientResponseError to the error they originated as
		self.error_handlers = {
			500: http_error.InternalServerError,
		}

		for e in http_error.__dict__.values() :
			if isinstance(e, http_error.HttpError) and e.status not in self.error_handlers :
				self.error_handlers[e.status] = e


	def initialize(self: 'Client', token: Optional[str] = None, _login: Optional[Callable[[str], LoginResponse]] = None) :
		"""
		Initializes the internal bot credentials and auth token. should only be called once on application startup.

		:param token: base64 encoded bot login token generated from the fuzz.ly bot creation endpoint
		:param _login: async function to perform bot authentication with. omit to default to `/v1/bot_login`. must accept `{ 'token': 'bot token string' }` as arg and return a `fuzzly.models.auth.LoginResponse` model.
		"""

		self._login: Gateway = _login or Gateway(AccountHost + '/v1/bot_login', LoginResponse, 'POST')
		self._token: Optional[str] = token
		self._auth: Optional[str] = None
		self._expires: int = 0
		self._limit: int = 0


	async def login(self: 'Client') -> None :
		self._expires += 60  # bump expiration a little bit so we don't try to re-auth twice
		login_response: LoginResponse = await self._login({ 'token': self._token })
		self._auth = login_response.token.token
		self._limit = int(login_response.token.expires.timestamp()) - 60  # cutoff for when re-auth is *required*, to ensure we never pass expired credentials
		self._expires = self._limit - 540  # token expiration, minus a few minutes to give time to re-auth asyncly


	@staticmethod
	def error_handler(func: Callable) -> Callable :
		"""
		Transforms aiohttp.ClientResponseError back to their original kh_common.exceptions.http_error.HttpError instance for re-raising and/or handling internally.

		Usage
		```
		class MyClient(Client) :
			@Client.authenticated
			async test(auth: str = None) -> str :
				return 'success'
		```
		:param func: async callable that performs an aiohttp.request and potentially raises an aiohttp.ClientResponseError
		"""

		if not iscoroutinefunction(func if isfunction(func) else getattr(func, '__call__', func)) :
			raise NotImplementedError('provided func is not defined as async. did you pass in a Gateway?')

		async def wrapper(self: 'Client', *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Any :
			try :
				return await func(self, *args, **kwargs)

			except ClientResponseError as e :
				# gateway will need changes made to it in order to be able to pull the response body and fully rebuild the error, for now just call the correct error type
				if e.status in self.error_handlers :
					raise self.error_handlers[e.status](self.error_handlers[e.status].__name__)

				raise

		# necessary to preserve the argspec
		sig = signature(func)
		dec_params = [p for p in sig.parameters.values() if p.kind is Parameter.POSITIONAL_OR_KEYWORD]

		wrapper.__signature__ = sig.replace(parameters=dec_params)
		wrapper.__name__ = func.__name__
		wrapper.__doc__ = func.__doc__
		wrapper.__wrapped__ = func
		wrapper.__qualname__ = func.__qualname__
		wrapper.__kwdefaults__ = getattr(func, '__kwdefaults__', None)
		wrapper.__dict__.update(func.__dict__)

		return wrapper


	@staticmethod
	def authenticated(func: Callable) -> Callable :
		"""
		Injects an authenticated bot token into the 'auth' kwarg of the passed function

		Usage
		```
		class MyClient(Client) :
			@Client.authenticated
			async test(auth: str = None) -> str :
				return 'success'
		```
		:param func: async callable that accepts an `auth` kwarg that represents authenticated bot bearer token. (as opposed to a login bot token returned from bot_create)
		"""

		if not iscoroutinefunction(func if isfunction(func) else getattr(func, '__call__', func)) :
			raise NotImplementedError('provided func is not defined as async and is not supported.')

		async def wrapper(self: 'Client', *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Any :
			if time() > self._expires and self._token :
				login_task: Task = ensure_future(self.login())

				if time() > self._limit :
					# basically, our auth has already expired, so make sure it's refreshed before continuing
					await login_task

			# only provide auth if it's not included by the user
			if 'auth' not in kwargs :
				kwargs['auth'] = self._auth

			return await func(self, *args, **kwargs)


		# necessary to preserve the argspec
		sig = signature(func)
		dec_params = [p for p in sig.parameters.values() if p.kind is Parameter.POSITIONAL_OR_KEYWORD]

		wrapper.__signature__ = sig.replace(parameters=dec_params)
		wrapper.__name__ = func.__name__
		wrapper.__doc__ = func.__doc__
		wrapper.__wrapped__ = func
		wrapper.__qualname__ = func.__qualname__
		wrapper.__kwdefaults__ = getattr(func, '__kwdefaults__', None)
		wrapper.__dict__.update(func.__dict__)

		return wrapper
