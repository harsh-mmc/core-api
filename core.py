import requests
import json
import os
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.model import *
from app.auth.auth_bearer import JWTBearer
from app.auth.auth_handler import *
from .app.user import *
from .app.audit import *

def savefile(fileobj):
    content = fileobj.read()
    print(content)
    if not (os.path.isdir(CONTRACT_FOLDER)):
        os.mkdir(CONTRACT_FOLDER)
    with open(f'{CONTRACT_FOLDER}/{TEMP_FILE_NAME}', 'wb') as f:
        f.write(content)

app = FastAPI()

origins = ["*"]
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

@app.post('/login')
async def login(data: UserLoginSchema):
    return userLogin(data)


@app.post('/uploadfile')
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

    return {"Filename" : data.filename, "Content Type" : data.content_type, "RequestID": request_id, "Key": filekey}

@app.post('/results')
async def results(data: AuditRequest, auth: str = Depends(JWTBearer())):
    usermail = auth['usermail']
    return fetchResults(data = data, usermail= usermail)

@app.get('/history')
async def history(auth: str = Depends(JWTBearer())):
    usermail = auth['usermail']
    return fetchHistory(usermail)


@app.get('/')
async def default():
    return 'server is running'

if __name__ == '__main__':
    uvicorn.run('core:app', port = 8000, reload=True)
