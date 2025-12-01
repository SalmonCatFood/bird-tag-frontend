# Handles WebSocket $disconnect events.
import os
import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CONNECTION_TABLE'])

def handler(event, context):
    logger.info(f"DisconnectHandler invoked event: {json.dumps(event)}")

    connection_id = event['requestContext']['connectionId']

    # 删除连接记录
    table.delete_item(Key={'connection_id': connection_id})

    return {'statusCode': 200, 'body': 'disconnected'}
