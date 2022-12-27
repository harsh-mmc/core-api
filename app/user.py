from .variables_setup import *
from .model import *
from .auth.auth_handler import signJWT

def ensureTable():
    dynamo_client = boto3.client('dynamodb', region_name = 'us-east-2')
    existing_tables = dynamo_client.list_tables()['TableNames']
    if TABLE_NAME not in existing_tables:
        dynamo_client.create_table(
            AttributeDefinitions = [
                {
                    'AttributeName': 'usermail',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'request_id',
                    'AttributeType': 'S'
                }
            ],
            KeySchema = [
                {
                    'AttributeName': 'usermail',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'request_id',
                    'KeyType': 'RANGE'
                }
            ],
            ProvisionedThroughput = {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
            TableName = TABLE_NAME,
        )
    
    if USER_TABLE not in existing_tables:
        dynamo_client.create_table(
            AttributeDefinitions = [
                {
                    'AttributeName': 'usermail',
                    'AttributeType': 'S'
                },
            ],
            KeySchema = [
                {
                    'AttributeName': 'usermail',
                    'KeyType': 'HASH'
                },
            ],
            ProvisionedThroughput = {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
            TableName = USER_TABLE,
        )

def userSignUp(data: UserSchema):
    table = db.Table(USER_TABLE)
    try:
        table.put_item(
            Item = {
                'usermail': data.email,
                'username': data.fullname,
                'password': data.password,
            }
        )
        return f'User {data.email} signed up, welcome {data.fullname}!'
    except BaseException as error:
        return str(error)

def userLogin(data: UserLoginSchema):
    table = db.Table(USER_TABLE)
    response = table.get_item(
        Key = {
            'usermail': data.email
        }
    )
    item = response['Item']
    if not item['password']==data.password:
        return {'Error': 'Wrong Login Details'}
    else :
        return signJWT(data.email)