from datetime import datetime
from enum import Enum, unique
from typing import Optional

from pydantic import BaseModel


@unique
class AuthAlgorithm(Enum) :
	ed25519: str = 'ed25519'


class TokenResponse(BaseModel) :
	version: str
	algorithm: AuthAlgorithm
	key_id: int
	issued: datetime
	expires: datetime
	token: str


class LoginResponse(BaseModel) :
	user_id: int
	handle: str
	name: Optional[str]
	mod: bool
	token: TokenResponse
