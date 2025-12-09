import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['METADATA_TABLE'])

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

def lambda_handler(event, context):
    """
    Get card details for a specific file
    Expects file_id from path parameters or query string
    Expects user_id from API Gateway authorizer context for authorization
    Returns all fields except user_id
    """
    logger.info(f"GetCardDetailsLambda invoked with event: {json.dumps(event)}")
    
    try:
        # Get file_id from path parameters or query string
        path_params = event.get('pathParameters', {}) or {}
        query_params = event.get('queryStringParameters', {}) or {}
        file_id = path_params.get('file_id') or query_params.get('file_id')
        
        if not file_id:
            logger.error("No file_id provided")
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Bad Request: file_id is required'
                })
            }
        
        # Get user_id from authorizer context (for authorization check)
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        user_id = authorizer.get('user_id') or authorizer.get('principalId')
        
        if not user_id:
            logger.error("No user_id found in authorizer context")
            return {
                'statusCode': 401,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Unauthorized: user_id not found'
                })
            }
        
        logger.info(f"Getting card details for file_id: {file_id}, user_id: {user_id}")
        
        # Get item from DynamoDB
        try:
            response = table.get_item(
                Key={'file_id': file_id}
            )
            
            if 'Item' not in response:
                logger.warning(f"File not found: {file_id}")
                return {
                    'statusCode': 404,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                        'Access-Control-Allow-Methods': 'GET,OPTIONS',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({
                        'error': 'Not Found: File not found'
                    })
                }
            
            item = response['Item']
            
            # Verify that the file belongs to the authenticated user
            item_user_id = item.get('user_id')
            if item_user_id != user_id:
                logger.warning(f"Access denied: file belongs to {item_user_id}, but request from {user_id}")
                return {
                    'statusCode': 403,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                        'Access-Control-Allow-Methods': 'GET,OPTIONS',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({
                        'error': 'Forbidden: You do not have access to this file'
                    })
                }
            
            # Convert Decimal types
            file_data = convert_decimals(item)
            
            # Remove user_id from response (as per requirement)
            file_data.pop('user_id', None)
            
            # Ensure all fields have default values
            file_data.setdefault('file_id', '')
            file_data.setdefault('file_type', 'unknown')
            file_data.setdefault('status', 'PENDING')
            file_data.setdefault('tags', {})
            file_data.setdefault('s3_url', None)
            file_data.setdefault('thumbnail_url', None)
            file_data.setdefault('upload_timestamp', '')
            file_data.setdefault('additional_metadata', {})
            
            logger.info(f"Successfully retrieved card details for file_id: {file_id}")
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(file_data, default=str)
            }
            
        except ClientError as e:
            logger.error(f"DynamoDB operation failed: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Internal server error',
                    'message': 'Failed to retrieve file details'
                })
            }
        
    except Exception as e:
        logger.error(f"Error getting card details: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

