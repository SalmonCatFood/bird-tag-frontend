# Handles updates to the meta database and sends updates to connected WebSocket clients.
import os
import json
import logging
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.types import TypeDeserializer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
connections_table = dynamodb.Table(os.environ['CONNECTION_TABLE'])

# 获取 WebSocket 端点
websocket_endpoint = os.environ.get('WEBSOCKET_ENDPOINT')
if not websocket_endpoint:
    raise ValueError('WEBSOCKET_ENDPOINT environment variable is required')

apigw = boto3.client(
    'apigatewaymanagementapi',
    endpoint_url=websocket_endpoint
)

deserializer = TypeDeserializer()

def _deserialize_ddb_item(new_image):
    """将 DynamoDB Streams 的 NewImage 结构转成普通 Python dict"""
    return {k: deserializer.deserialize(v) for k, v in new_image.items()}

def convert_decimals(obj):
    """
    递归地将 Decimal 类型转换为 int 或 float
    """
    if isinstance(obj, Decimal):
        # 如果是整数，转换为 int，否则转换为 float
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj

def handler(event, context):
    logger.info(f"MetaDbUpdateLambda triggered with event: {json.dumps(event)}")
    
    # 记录 WebSocket 端点（用于调试）
    logger.info(f"WebSocket endpoint: {websocket_endpoint}")
    
    for record in event.get('Records', []):
        if record.get('eventName') not in ('INSERT', 'MODIFY'):
            logger.info(f"Skipping event: {record.get('eventName')}")
            continue

        ddb_new_image = record['dynamodb'].get('NewImage')
        if not ddb_new_image:
            logger.warning("No NewImage in record")
            continue

        # 反序列化 NewImage
        try:
            item = _deserialize_ddb_item(ddb_new_image)
        except Exception as e:
            logger.error(f"Failed to deserialize item: {e}")
            continue

        user_id = item.get('user_id')
        file_id = item.get('file_id')
        thumbnail_url = item.get('thumbnail_url')
        tags = item.get('tags', {})
        file_type = item.get('file_type')
        upload_timestamp = item.get('upload_timestamp')

        if not user_id or not file_id:
            logger.warning(f"Missing user_id or file_id: user_id={user_id}, file_id={file_id}")
            continue

        # 转换 tags 中的 Decimal 类型
        tags = convert_decimals(tags) if tags else {}

        payload = {
            'type': 'FILE_UPDATE',
            'file_id': file_id,
            'file_type': file_type,
            'thumbnail_url': thumbnail_url,
            'tags': tags,
            'upload_timestamp': upload_timestamp
        }

        logger.info(f"Processing update for file_id={file_id}, user_id={user_id}")
        logger.info(f"Payload: {json.dumps(payload)}")

        # 查询该用户的所有连接
        try:
            response = connections_table.scan(
                FilterExpression=Attr('user_id').eq(user_id)
            )
            connections = response.get('Items', [])
            logger.info(f"Found {len(connections)} connections for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to query connections: {e}")
            continue

        if not connections:
            logger.warning(f"No active connections found for user {user_id}")
            continue

        # 推送消息到每个连接
        success_count = 0
        failed_count = 0
        
        for conn_item in connections:
            conn_id = conn_item.get('connection_id')
            if not conn_id:
                logger.warning(f"Connection item missing connection_id: {conn_item}")
                continue

            try:
                # 直接传 JSON 字符串，不需要 encode
                apigw.post_to_connection(
                    ConnectionId=conn_id,
                    Data=json.dumps(payload)  # 现在可以正常序列化了
                )
                logger.info(f"✅ Successfully sent message to connection: {conn_id}")
                success_count += 1
            except apigw.exceptions.GoneException:
                # 连接已失效，删除记录
                logger.warning(f"Connection {conn_id} is gone, deleting from table")
                try:
                    connections_table.delete_item(
                        Key={'connection_id': conn_id}
                    )
                    logger.info(f"Deleted stale connection: {conn_id}")
                except Exception as e:
                    logger.error(f"Failed to delete stale connection {conn_id}: {e}")
                failed_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to send to connection {conn_id}: {str(e)}")
                failed_count += 1

        logger.info(f"Message delivery summary: {success_count} succeeded, {failed_count} failed")

    return {'statusCode': 200, 'body': 'processed'}