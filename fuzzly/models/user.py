from pydantic import BaseModel

from ._shared import Badge, User, UserPortable, UserPrivacy, Verified


class UpdateSelf(BaseModel) :
	name: str = None
	privacy: UserPrivacy = None
	icon: str = None
	website: str = None
	description: str = None


class SetMod(BaseModel) :
	handle: str
	mod: bool


class SetVerified(BaseModel) :
	handle: str
	verified: Verified


class Follow(BaseModel) :
	handle: str
