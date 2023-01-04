from pydantic import BaseModel

class Token(BaseModel):
    access_token: str

class Uploaded(BaseModel):
    Filename: str
    Content_Type: str
    RequestID: str
    Key: str

class Result(BaseModel):
    usermail: str
    request_id: str
    key: str
    slither: str
    mythril: str
    manticore: str

class History(BaseModel):
    history: list[Result]