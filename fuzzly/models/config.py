from enum import Enum, unique
from typing import Dict, List, Literal, Optional, Set, Union

from avrofastapi.schema import AvroInt
from pydantic import BaseModel, conbytes, validator

from ._shared import PostId, _post_id_converter


UserConfigKeyFormat: str = 'user.{user_id}'


class BannerStore(BaseModel) :
	banner: Optional[str]


class CostsStore(BaseModel) :
	costs: int


@unique
class ConfigType(str, Enum) :
	banner: str = 'banner'
	costs: str = 'costs'


class UpdateBannerRequest(BaseModel) :
	config: Literal[ConfigType.banner]
	value: BannerStore


class UpdateCostsRequest(BaseModel) :
	config: Literal[ConfigType.costs]
	value: CostsStore


UpdateConfigRequest: type = Union[UpdateBannerRequest, UpdateCostsRequest]


class SaveSchemaResponse(BaseModel) :
	fingerprint: str


class FundingResponse(BaseModel) :
	funds: int
	costs: int


class BannerResponse(BannerStore) :
	pass


class BlockingBehavior(Enum) :
	hide: str = 'hide'
	omit: str = 'omit'


class CssProperty(Enum) :
	background_attachment: str = 'background_attachment'
	background_position: str = 'background_position'
	background_repeat: str = 'background_repeat'
	background_size: str = 'background_size'

	transition: str = 'transition'
	fadetime: str = 'fadetime'
	warning: str = 'warning'
	error: str = 'error'
	valid: str = 'valid'
	general: str = 'general'
	mature: str = 'mature'
	explicit: str = 'explicit'
	icolor: str = 'icolor'
	bg0color: str = 'bg0color'
	bg1color: str = 'bg1color'
	bg2color: str = 'bg2color'
	bg3color: str = 'bg3color'
	blockquote: str = 'blockquote'
	textcolor: str = 'textcolor'
	bordercolor: str = 'bordercolor'
	linecolor: str = 'linecolor'
	borderhover: str = 'borderhover'
	subtle: str = 'subtle'
	shadowcolor: str = 'shadowcolor'
	activeshadowcolor: str = 'activeshadowcolor'
	screen_cover: str = 'screen_cover'
	border_size: str = 'border_size'
	border_radius: str = 'border_radius'
	wave_color: str = 'wave_color'
	stripe_color: str = 'stripe_color'
	main: str = 'main'
	pink: str = 'pink'
	yellow: str = 'yellow'
	green: str = 'green'
	blue: str = 'blue'
	orange: str = 'orange'
	red: str = 'red'
	cyan: str = 'cyan'
	violet: str = 'violet'
	bright: str = 'bright'
	funding: str = 'funding'
	notification_text: str = 'notification_text'
	notification_bg: str = 'notification_bg'


class UserConfig(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[List[str]]]
	blocked_users: Optional[List[int]]
	wallpaper: Optional[conbytes(min_length=8, max_length=8)]
	css_properties: Optional[Dict[str, Union[CssProperty, AvroInt, str]]]


class UserConfigRequest(BaseModel) :
	_post_id_converter = validator('wallpaper', pre=True, always=True, allow_reuse=True)(_post_id_converter)

	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[Set[str]]]
	blocked_users: Optional[List[str]]
	wallpaper: Optional[PostId]
	css_properties: Optional[Dict[CssProperty, str]]


class UserConfigResponse(BaseModel) :
	blocking_behavior: Optional[BlockingBehavior]
	blocked_tags: Optional[List[Set[str]]]
	blocked_users: Optional[List[str]]
	wallpaper: Optional[str]
