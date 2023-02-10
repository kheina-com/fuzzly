from typing import Any

import pytest

from fuzzly.models.post import PostId


@pytest.mark.parametrize(
	'value, expected',
	[
		(0, 'AAAAAAAA'),
		(2**48-1, '________'),
		('JPIlC520', 'JPIlC520'),
		(b'$\xf2%\x0b\x9d\xb4', 'JPIlC520')
	]
)
def test_PostId_ValidValue(value: Any, expected: str) :
	assert PostId(value) == expected


@pytest.mark.parametrize(
	'value',
	[-1, 2**48, 'abcd123', 'abcd12345', b'\x00\x00\x00\x00\x00\x00\x00', b'\x00\x00\x00\x00\x00']
)
def test_PostId_InvalidValue(value: Any) :
	with pytest.raises(ValueError) :
		assert PostId(value)
