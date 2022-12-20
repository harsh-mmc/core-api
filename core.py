import boto3
import requests
import json
import os
import sys
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import uvicorn

BUCKET_NAME = 'labs-smart-contract-security-audit'
CONTRACT_FOLDER = 'core-contracts'
TEMP_FILE_NAME = 'temporary'
TABLE_NAME = 'Smart-Contract-Audit'
SLITHER_URL = 'http://127.0.0.1:8001'

s3 = boto3.resource('s3')
db = boto3.resource('dynamodb', region_name = 'us-east-2')

class AuditRequest(BaseModel):
    request_id: str
    key: str

def ensureTable():
    dynamo_client = boto3.client('dynamodb', region_name = 'us-east-2')
    existing_tables = dynamo_client.list_tables()['TableNames']
    if TABLE_NAME not in existing_tables:
        dynamo_client.create_table(
            AttributeDefinitions = [
                {
                    'AttributeName': 'request_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'key',
                    'AttributeType': 'S'
                }
            ],
            KeySchema = [
                {
                    'AttributeName': 'request_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'key',
                    'KeyType': 'RANGE'
                }
            ],
            ProvisionedThroughput = {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
            TableName = TABLE_NAME,
        )

"""def printfile(fileobj):
    content = fileobj.read()
    print(type(content))
    print(str(content))"""

def savefile(fileobj):
    content = fileobj.read()
    print(content)
    if not (os.path.isdir(CONTRACT_FOLDER)):
        os.mkdir(CONTRACT_FOLDER)
    with open(f'{CONTRACT_FOLDER}/{TEMP_FILE_NAME}', 'wb') as f:
        f.write(content)

app = FastAPI()

@app.on_event('startup')
async def startup():
    ensureTable()

@app.post('/uploadfile')
async def upload_file(data : UploadFile):
    print(data.filename)
    file = data.file
    print(type(file))
    #printfile(file)
    """Generate a unique request ID for this request"""
    request_id = str(uuid4())
    filekey = request_id[:8] + str(data.filename)
    """Save the file into temporary storage"""
    savefile(file)
    """Upload the file in the s3 bucket, with key as file name"""
    s3.Bucket(BUCKET_NAME).upload_file(f'{CONTRACT_FOLDER}/{TEMP_FILE_NAME}', filekey)

    """Now enter request_id and key in the dynamodb database"""
    table = db.Table(TABLE_NAME)
    table.put_item(
        Item={
            'request_id' : request_id,
            'key' : filekey,
            'slither': 'awaited',
            'mythril': 'awaited',
            'manticore': 'awaited',
        }
    )

    """Now send post requests to slither, mythril and manticore API"""
    slither_output = ''
    try:
        slither_response = requests.post(f'{SLITHER_URL}/vulnerable', json={'contract_key' : filekey})
        slither_output = json.dumps(slither_response.json())
    except BaseException as error:
        slither_output = f"Something went wrong, here's the error:\n{error}"
    
    """Update the table with slither response"""
    table.update_item(
        Key = {
            'request_id': request_id,
            'key': filekey,
        },
        UpdateExpression = 'SET slither = :newslither',
        ExpressionAttributeValues = {
            ':newslither': slither_output
        }
    )

    return {"Filename" : data.filename, "Content Type" : data.content_type, "RequestID": request_id, "Key": filekey}

@app.post('/results')
async def fetchResults(data: AuditRequest):
    table = db.Table(TABLE_NAME)
    try:
        fetchResponse = table.get_item(
            Key = {
                'request_id': data.request_id,
                'key': data.key,
            }
        )
        record = fetchResponse['Item']
        return record
    except BaseException as error:
        return str(error)

@app.get('/')
async def default():
    return 'server is running'

if __name__ == '__main__':
    uvicorn.run('core:app', port = 8000, reload=True)
