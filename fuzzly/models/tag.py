from enum import Enum, unique
from typing import Dict, List, Optional

from pydantic import BaseModel

from .user import UserPortable


@unique
class TagGroupPortable(Enum) :
	artist: str = 'artist'
	subject: str = 'subject'
	sponsor: str = 'sponsor'
	species: str = 'species'
	gender: str = 'gender'
	misc: str = 'misc'


class TagGroups(Dict[TagGroupPortable, List[str]]) :
	# TODO: write a better docstr for this
	"""
```python
class TagGroups(Dict[TagGroupPortable, List[str]]) :
	pass
```
"""
	pass


class Tag(BaseModel) :
	tag: str
	owner: Optional[UserPortable]
	group: TagGroupPortable
	deprecated: bool
	inherited_tags: List[str]
	description: Optional[str]
	count: int
