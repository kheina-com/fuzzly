from typing import Dict

from kh_common.config.constants import Environment, environment


AuthHost: str
UploadHost: str
TagHost: str
PostHost: str
AccountHost: str
UserHost: str
ConfigHost: str
AvroHost: str


CONSTANTS: Dict[Environment, Dict[str, str]] = {
	Environment.test: {
		'AuthHost': 'http://127.0.0.1:5000',
		'UploadHost': 'http://localhost:5001',
		'TagHost': 'http://localhost:5002',
		'PostHost': 'http://localhost:5003',
		'AccountHost': 'http://localhost:5004',
		'UserHost': 'http://localhost:5005',
		'ConfigHost': 'http://localhost:5006',
		'AvroHost': 'http://localhost:5007',
	},
	Environment.local: {
		'AuthHost': 'http://127.0.0.1:5000',
		'UploadHost': 'http://localhost:5001',
		'TagHost': 'http://localhost:5002',
		'PostHost': 'http://localhost:5003',
		'AccountHost': 'http://localhost:5004',
		'UserHost': 'http://localhost:5005',
		'ConfigHost': 'http://localhost:5006',
		'AvroHost': 'http://localhost:5007',
	},
	Environment.dev: {
		'AuthHost': 'https://auth-dev.fuzz.ly',
		'UploadHost': 'https://upload-dev.fuzz.ly',
		'TagHost': 'https://tags-dev.fuzz.ly',
		'PostHost': 'https://posts-dev.fuzz.ly',
		'AccountHost': 'https://account-dev.fuzz.ly',
		'UserHost': 'https://users-dev.fuzz.ly',
		'ConfigHost': 'https://config-dev.fuzz.ly',
		'AvroHost': 'https://avro-dev.fuzz.ly',
	},
	Environment.prod: {
		'AuthHost': 'https://auth.fuzz.ly',
		'UploadHost': 'https://upload.fuzz.ly',
		'TagHost': 'https://tags.fuzz.ly',
		'PostHost': 'https://posts.fuzz.ly',
		'AccountHost': 'https://account.fuzz.ly',
		'UserHost': 'https://users.fuzz.ly',
		'ConfigHost': 'https://config.fuzz.ly',
		'AvroHost': 'https://avro.fuzz.ly',
	},
}


# add the variables from the environment to the module
locals().update(CONSTANTS[environment])

# delete extraneous data
del CONSTANTS
