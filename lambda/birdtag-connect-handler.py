#Handles WebSocket $connect events.
import os
import json
import logging
import boto3
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTION_TABLE'])

def handler(event, context):
    logger.info(f"ConnectHandler invoked event: {json.dumps(event)}")

    connection_id = event['requestContext']['connectionId']
    user_id = event['requestContext']['authorizer']['user_id']
    now_iso = datetime.now(timezone.utc).isoformat()

    # 写入连接记录
    table.put_item(Item={
        'connection_id': connection_id,
        'user_id': user_id,
        'connected_at': now_iso,
        'last_seen': now_iso
    })

    return {'statusCode': 200, 'body': 'connected'}
