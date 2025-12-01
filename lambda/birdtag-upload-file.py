import os
import json
import logging
import boto3
import uuid
import jwt
from jwt import PyJWKClient
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['METADATA_TABLE'])

# Cognito configuration
COGNITO_USERPOOL_ID = os.getenv('COGNITO_USERPOOL_ID')
COGNITO_REGION = os.getenv('COGNITO_REGION', 'ap-southeast-2')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
EXPECTED_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USERPOOL_ID}"

def verify_jwt_and_get_user_id(token: str):
    """Verify JWT token and extract user_id"""
    try:
        jwks_url = f"{EXPECTED_ISSUER}/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=EXPECTED_ISSUER,
        )
        # Extract user_id from token payload
        user_id = payload.get('sub') or payload.get('cognito:username') or payload.get('user_id')
        return user_id
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return None

def handler(event, context):
    logger.info(f"UploadFileLambda invoked with event: {json.dumps(event)}")

    # Try to get user_id from authorizer context first (if REST API authorizer is configured)
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('user_id')
    
    # If not in authorizer context, extract from Authorization header
    if not user_id:
        try:
            # Get Authorization header
            headers = event.get('headers', {}) or {}
            # API Gateway may lowercase headers
            auth_header = headers.get('Authorization') or headers.get('authorization') or ''
            
            if auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '')
                user_id = verify_jwt_and_get_user_id(token)
            
            if not user_id:
                logger.warning("Could not extract user_id from token or authorizer")
                user_id = 'unknown_user'
        except Exception as e:
            logger.error(f"Error extracting user_id: {str(e)}")
            user_id = 'unknown_user'
    
    logger.info(f"Extracted user_id: {user_id}")

    # 假设从 body 中获取 filename 和 content_type
    body = json.loads(event.get('body','{}'))
    filename = body.get('filename')
    content_type = body.get('content_type')

    file_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # 推断 file_type
    if content_type.startswith('image/'):
        file_type = 'image'
    elif content_type.startswith('video/'):
        file_type = 'video'
    elif content_type.startswith('audio/'):
        file_type = 'audio'
    else:
        file_type = 'unknown'

    # 构造 S3 key（示例）
    key = f"{file_type}/{user_id}_{file_id}.{filename.split('.')[-1]}"
    file_id = f"{user_id}_{file_id}"

    # 插入初始 metadata
    table.put_item(Item={
        'file_id': file_id,
        'user_id': user_id,
        's3_url': None,
        'thumbnail_url': None,
        'file_type': file_type,
        'tags': {},
        'upload_timestamp': now_iso,
        'additional_metadata': {}
    })

    # 生成 presigned URL（举例用 s3 client）
    s3 = boto3.client('s3')
    bucket = os.environ.get('IMAGES_S3') if file_type=='image' else \
             os.environ.get('VIDEO_S3') if file_type=='video' else \
             os.environ.get('AUDIO_S3') if file_type=='audio' else None

    if bucket:
        presign_url = s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket, 'Key': key, 'ContentType': content_type},
            ExpiresIn=3600
        )
    else:
        presign_url = None

    response = {
        'file_id': file_id,
        'presign_url': presign_url,
        's3_key': key
    }

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*', 
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'file_id': file_id,
            'presign_url': presign_url,
            's3_key': key
        })
    }
