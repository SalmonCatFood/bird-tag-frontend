# $connect authorizer, validates JWT tokens for WebSocket connections.
import os
import json
import jwt
from jwt import PyJWKClient
from datetime import datetime, timezone

COGNITO_USERPOOL_ID = os.getenv("COGNITO_USERPOOL_ID")
COGNITO_REGION      = os.getenv("COGNITO_REGION", "ap-southeast-2")
EXPECTED_AUDIENCE   = os.getenv("COGNITO_CLIENT_ID")
EXPECTED_ISSUER     = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USERPOOL_ID}"

def verify_jwt(token: str):
    jwks_url = f"{EXPECTED_ISSUER}/.well-known/jwks.json"
    jwks_client = PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=EXPECTED_AUDIENCE,
        issuer=EXPECTED_ISSUER,
    )
    return payload

def generate_policy(principal_id, effect, resource_arn, context=None):
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": resource_arn
            }]
        }
    }
    if context:
        policy["context"] = context
    return policy

def handler(event, context):
    print(f"[DEBUG] Event: {json.dumps(event)}")
    try:
        token = (event.get("queryStringParameters") or {}).get("token")
        if not token:
            raise ValueError("Missing token")

        payload = verify_jwt(token)
        user_id = payload.get("sub") or payload.get("user_id") or "unknown"

        return generate_policy(
            principal_id=user_id,
            effect="Allow",
            resource_arn=event["methodArn"],
            context={
                "user_id": user_id,
                "email": payload.get("email", ""),
                "issued_at": str(datetime.now(timezone.utc))
            }
        )
    except Exception as e:
        print(f"[ERROR] Authorization failed: {e}")
        return generate_policy(
            principal_id="unauthorized",
            effect="Deny",
            resource_arn=event.get("methodArn", "*"),
            context={"error": str(e)}
        )
