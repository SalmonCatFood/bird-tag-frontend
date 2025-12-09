# REST API authorizer, validates JWT tokens for REST API requests.
# This is separate from the WebSocket authorizer to handle different event formats.
import os
import json
import jwt
from jwt import PyJWKClient
from datetime import datetime, timezone

COGNITO_USERPOOL_ID = os.getenv("COGNITO_USERPOOL_ID")
COGNITO_REGION = os.getenv("COGNITO_REGION", "ap-southeast-2")
EXPECTED_AUDIENCE = os.getenv("COGNITO_CLIENT_ID")
EXPECTED_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USERPOOL_ID}"

def verify_jwt(token: str):
    """Verify JWT token and return payload"""
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
    """Generate IAM policy for API Gateway"""
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
    """
    REST API Lambda Authorizer
    Expects token in Authorization header: "Bearer <token>"
    
    Event structure for REST API:
    {
        "type": "TOKEN" or "REQUEST",
        "methodArn": "arn:aws:execute-api:...",
        "authorizationToken": "Bearer <token>" (for TOKEN type),
        "headers": { "Authorization": "Bearer <token>" } (for REQUEST type)
    }
    """
    print(f"[DEBUG] REST Authorizer Event: {json.dumps(event)}")
    
    try:
        token = None
        
        # Handle TOKEN type authorizer (simpler, recommended for REST API)
        if event.get("type") == "TOKEN":
            auth_token = event.get("authorizationToken", "")
            if auth_token.startswith("Bearer "):
                token = auth_token.replace("Bearer ", "").strip()
            else:
                token = auth_token.strip()
        
        # Handle REQUEST type authorizer (more complex, can access full request)
        elif event.get("type") == "REQUEST":
            headers = event.get("headers", {}) or {}
            # API Gateway may lowercase headers
            auth_header = headers.get("Authorization") or headers.get("authorization") or ""
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "").strip()
            else:
                token = auth_header.strip()
        
        # Fallback: try to get from authorizationToken field
        if not token:
            auth_token = event.get("authorizationToken", "")
            if auth_token.startswith("Bearer "):
                token = auth_token.replace("Bearer ", "").strip()
            else:
                token = auth_token.strip()
        
        if not token:
            raise ValueError("Missing token in Authorization header or authorizationToken field")
        
        print(f"[DEBUG] Extracted token: {token[:20]}...")
        
        # Verify JWT token
        payload = verify_jwt(token)
        user_id = payload.get("sub") or payload.get("user_id") or "unknown"
        
        print(f"[DEBUG] Token verified, user_id: {user_id}")
        
        # Get method ARN (required for policy)
        method_arn = event.get("methodArn", "*")
        original_method_arn = method_arn
        
        # For path parameters, ensure Resource ARN uses wildcard to match any path parameter value
        # This is critical for resources with path parameters like /get-card-details/{file_id}
        # API Gateway passes the actual path value in methodArn, but policy should use wildcard
        # Example: arn:aws:execute-api:region:account:api-id/stage/GET/get-card-details/abc123
        # Should become: arn:aws:execute-api:region:account:api-id/stage/GET/get-card-details/*
        if method_arn and method_arn != "*":
            arn_parts = method_arn.split("/")
            # Format after split: [arn:aws:execute-api:region:account:api-id, stage, METHOD, path, param-value]
            # For /get-card-details/{file_id} with value abc123:
            # [0]: arn:aws:execute-api:region:account:api-id
            # [1]: stage (e.g., "dev")
            # [2]: METHOD (e.g., "GET")
            # [3]: path (e.g., "get-card-details")
            # [4]: param-value (e.g., "abc123")
            # We need at least 5 parts (including the path parameter value)
            if len(arn_parts) >= 5:
                # Replace the last part (path parameter value) with wildcard
                resource_base = "/".join(arn_parts[:-1])
                method_arn = f"{resource_base}/*"
                print(f"[DEBUG] Converted Resource ARN from specific to wildcard")
                print(f"[DEBUG]   Original: {original_method_arn}")
                print(f"[DEBUG]   Final:    {method_arn}")
        
        print(f"[DEBUG] Method ARN for policy: {method_arn}")
        
        # Generate policy with user context
        policy = generate_policy(
            principal_id=user_id,
            effect="Allow",
            resource_arn=method_arn,
            context={
                "user_id": user_id,
                "email": payload.get("email", ""),
                "issued_at": str(datetime.now(timezone.utc))
            }
        )
        
        print(f"[DEBUG] Policy generated: {json.dumps(policy)}")
        return policy
        
    except Exception as e:
        print(f"[ERROR] Authorization failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Return deny policy
        method_arn = event.get("methodArn", "*")
        return generate_policy(
            principal_id="unauthorized",
            effect="Deny",
            resource_arn=method_arn,
            context={"error": str(e)}
        )

