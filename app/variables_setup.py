import boto3

BUCKET_NAME = 'labs-smart-contract-security-audit'
CONTRACT_FOLDER = 'solidity-contracts'
TEMP_FILE_NAME = 'temporary'
TABLE_NAME = 'Smart-Contract-Audit'
USER_TABLE = 'Smart-Contract-Users'
SLITHER_URL = 'http://127.0.0.1:8001'

s3 = boto3.resource('s3')
db = boto3.resource('dynamodb', region_name = 'us-east-2')