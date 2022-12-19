import boto3
import requests
import json
import os
import sys
from uuid import uuid4
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

def printfile(fileobj):
    content = fileobj.read()
    print(type(content))
    print(content)

app = FastAPI()

@app.post('/uploadfile')
async def upload_file(data : UploadFile):
    print(data.filename)
    file = data.file
    printfile(file)
    return {"Filename" : data.filename, "Content Type" : data.content_type}

@app.get('/')
async def default():
    return 'server is running'
