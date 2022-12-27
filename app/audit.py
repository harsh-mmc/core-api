from boto3.dynamodb.conditions import Key, Attr
from .model import *
from .variables_setup import *

def fetchHistory(usermail: str):
    table = db.Table(TABLE_NAME)
    try:
        history = table.query(
            KeyConditionExpression = Key('usermail').eq(usermail)
        )
        items = history['Items']
        return items
    except BaseException as error:
        return str(error)

def fetchResults(data: AuditRequest, usermail: str):
    table = db.Table(TABLE_NAME)
    try:
        fetchResponse = table.get_item(
            Key = {
                'usermail': usermail,
                'request_id': data.request_id,
            }
        )
        record = fetchResponse['Item']
        return record
    except BaseException as error:
        return str(error)