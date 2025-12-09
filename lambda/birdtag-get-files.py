import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['METADATA_TABLE'])

def handler(event, context):
    """
    Get all files for the authenticated user
    Expects user_id from API Gateway authorizer context
    """
    logger.info(f"GetFilesLambda invoked with event: {json.dumps(event)}")
    
    try:
        # Get user_id from authorizer context (set by API Gateway authorizer)
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        user_id = authorizer.get('user_id')
        
        # Fallback: try to get from principalId if user_id not in context
        if not user_id:
            user_id = authorizer.get('principalId')
        
        if not user_id:
            logger.error("No user_id found in authorizer context")
            return {
                'statusCode': 401,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Unauthorized: user_id not found'
                })
            }
        
        logger.info(f"Querying files for user_id: {user_id}")
        
        # Query DynamoDB for all files belonging to this user
        # Try to use GSI first, fall back to scan if GSI doesn't exist
        items = []
        
        try:
            # Check if GSI exists by trying to describe the table
            table_desc = table.meta.client.describe_table(TableName=table.name)
            gsi_list = table_desc.get('Table', {}).get('GlobalSecondaryIndexes', [])
            
            # Find a GSI on user_id (common names: user_id-index, user_id-GSI, etc.)
            user_id_gsi = None
            for gsi in gsi_list:
                index_name = gsi.get('IndexName', '')
                key_schema = gsi.get('KeySchema', [])
                # Check if this GSI has user_id as partition key
                for key in key_schema:
                    if key.get('AttributeName') == 'user_id' and key.get('KeyType') == 'HASH':
                        user_id_gsi = index_name
                        break
                if user_id_gsi:
                    break
            
            if user_id_gsi:
                # Use GSI for efficient query
                logger.info(f"Using GSI: {user_id_gsi}")
                response = table.query(
                    IndexName=user_id_gsi,
                    KeyConditionExpression=Key('user_id').eq(user_id)
                )
                items = response.get('Items', [])
                
                # Handle pagination
                while 'LastEvaluatedKey' in response:
                    response = table.query(
                        IndexName=user_id_gsi,
                        KeyConditionExpression=Key('user_id').eq(user_id),
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    items.extend(response.get('Items', []))
            else:
                # No GSI found, use scan with filter
                logger.warning("No GSI found on user_id, using scan (less efficient for large datasets)")
                from boto3.dynamodb.conditions import Attr
                response = table.scan(
                    FilterExpression=Attr('user_id').eq(user_id)
                )
                items = response.get('Items', [])
                
                # Handle pagination
                while 'LastEvaluatedKey' in response:
                    response = table.scan(
                        FilterExpression=Attr('user_id').eq(user_id),
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    items.extend(response.get('Items', []))
                    
        except ClientError as e:
            logger.error(f"DynamoDB operation failed: {e}")
            # Try scan as last resort
            try:
                from boto3.dynamodb.conditions import Attr
                logger.warning("Falling back to scan operation")
                response = table.scan(
                    FilterExpression=Attr('user_id').eq(user_id)
                )
                items = response.get('Items', [])
                
                # Handle pagination
                while 'LastEvaluatedKey' in response:
                    response = table.scan(
                        FilterExpression=Attr('user_id').eq(user_id),
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    items.extend(response.get('Items', []))
            except Exception as scan_error:
                logger.error(f"Scan also failed: {scan_error}")
                raise
        
        # Process items - DynamoDB resource automatically converts types
        # But we need to handle Decimal types for JSON serialization
        from decimal import Decimal
        
        def convert_decimals(obj):
            """Convert Decimal to float or int for JSON serialization"""
            if isinstance(obj, Decimal):
                if obj % 1 == 0:
                    return int(obj)
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(v) for v in obj]
            return obj
        
        files_list = []
        for item in items:
            try:
                # Convert Decimal types
                file_data = convert_decimals(item)
                
                # Ensure all required fields are present with defaults
                file_data.setdefault('file_id', '')
                file_data.setdefault('user_id', user_id)
                file_data.setdefault('file_type', 'unknown')
                file_data.setdefault('status', 'PENDING')
                file_data.setdefault('tags', {})
                file_data.setdefault('s3_url', '')
                file_data.setdefault('thumbnail_url', '')
                file_data.setdefault('upload_timestamp', '')
                file_data.setdefault('additional_metadata', {})
                
                files_list.append(file_data)
            except Exception as e:
                logger.error(f"Error processing item: {e}, item: {item}")
                continue
        
        # Sort by upload_timestamp (newest first)
        files_list.sort(
            key=lambda x: x.get('upload_timestamp', ''),
            reverse=True
        )
        
        logger.info(f"Found {len(files_list)} files for user {user_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Access-Control-Max-Age': '300',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(files_list, default=str)
        }
        
    except Exception as e:
        logger.error(f"Error getting files: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Access-Control-Max-Age': '300',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

