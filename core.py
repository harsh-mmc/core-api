import requests
import json
import os
import multiprocessing
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.model import *
from app.auth.auth_bearer import JWTBearer
from app.auth.auth_handler import *
from app.user import *
from app.audit import *
from app.response import *

def call_slither(filekey: str, usermail, request_id):
    table = db.Table(TABLE_NAME)
    slither_output = ''
    try:
        slither_response = requests.post(f'{SLITHER_URL}/vulnerable', json={'contract_key' : filekey})
        slither_output = json.dumps(slither_response.json())
    except BaseException as error:
        slither_output = f"Something went wrong, here's the error:\n{error}"
    """Update the table with slither response"""
    table.update_item(
        Key = {
            'usermail': usermail,
            'request_id': request_id,
        },
        UpdateExpression = 'SET slither = :newslither',
        ExpressionAttributeValues = {
            ':newslither': slither_output
        }
    )

def call_mythril(filekey:str, usermail, request_id):
    table = db.Table(TABLE_NAME)
    mythril_output = ''
    try:
        mythril_response = requests.post(f'{MYTHRIL_URL}/vulnerable', json={'contract_key' : filekey})
        mythril_output = json.dumps(mythril_response.json())
    except BaseException as error:
        mythril_output = f"Something went wrong, here's the error:\n{error}"
    """Update the table with slither response"""
    table.update_item(
        Key = {
            'usermail': usermail,
            'request_id': request_id,
        },
        UpdateExpression = 'SET mythril = :newmythril',
        ExpressionAttributeValues = {
            ':newmythril': mythril_output
        }
    )

def savefile(fileobj):
    content = fileobj.read()
    print(content)
    if not (os.path.isdir(CONTRACT_FOLDER)):
        os.mkdir(CONTRACT_FOLDER)
    with open(f'{CONTRACT_FOLDER}/{TEMP_FILE_NAME}', 'wb') as f:
        f.write(content)

app = FastAPI()

origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

@app.on_event('startup')
async def startup():
    ensureTable()

@app.post('/signup')
async def signup(data: UserSchema):
    return userSignUp(data)

@app.post('/login', response_model=Token)
async def login(data: UserLoginSchema):
    return userLogin(data)

"""@app.options('/uploadfile')
async def handle():
    msg = {"message": "success"}
    headers = {
        "Access-Control-Allow-Origin": "http://localhost:3000",
        "Access-Control-Allow-Methods": ["*"],
        "Access-Control-Allow-Headers": ["*"],
    }
    return JSONResponse(content=msg, headers=headers)"""

@app.post('/uploadfile', response_model=Uploaded)
async def upload_file(data : UploadFile, auth:str = Depends(JWTBearer())):
    print(data.filename)
    print(auth)
    file = data.file
    print(type(file))
    #printfile(file)
    """Gather the email ID from the token"""
    usermail = auth['usermail']
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
            'usermail': usermail,
            'request_id' : request_id,
            'key' : filekey,
            'slither': 'awaited',
            'mythril': 'awaited',
            'manticore': 'awaited',
        }
    )

    """Now send post requests to slither, mythril and manticore API"""
    p1 = multiprocessing.Process(target=call_slither, args=(filekey, usermail, request_id))
    p2 = multiprocessing.Process(target=call_mythril, args=(filekey, usermail, request_id))
    p1.start()
    p2.start()
    payload = {"Filename" : data.filename, "Content_Type" : data.content_type, "RequestID": request_id, "Key": filekey}
    header = {'Access-Control-Allow-Origin': '*'}
    #return JSONResponse(content=payload, headers=header)
    return payload

@app.post('/results', response_model=Result)
async def results(data: AuditRequest, auth: str = Depends(JWTBearer())):
    usermail = auth['usermail']
    return fetchResults(data = data, usermail= usermail)

@app.get('/history', response_model=History)
async def history(auth: str = Depends(JWTBearer())):
    usermail = auth['usermail']
    return fetchHistory(usermail)


@app.get('/')
async def default():
    return 'server is running'

if __name__ == '__main__':
    uvicorn.run('core:app', port = 5000, reload=True)
