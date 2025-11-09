# API Configuration Guide

## Overview

Before connecting the frontend to your AWS backend, you need to configure the API endpoints and authentication settings.

## Configuration File Location

The main configuration file is located at:
```
src/config/api.js
```

## Configuration Parameters

### 1. REST API Gateway URL

This is your REST API Gateway endpoint for file upload and metadata operations.

```javascript
REST_API_URL: 'https://YOUR_REST_API_ID.execute-api.YOUR_REGION.amazonaws.com/YOUR_STAGE'
```

**How to find it:**
1. Go to AWS Console → API Gateway
2. Select your REST API
3. Click "Stages" in the left menu
4. Select your stage (e.g., "prod")
5. Copy the "Invoke URL" at the top

**Example:**
```
https://abc123def4.execute-api.us-east-1.amazonaws.com/prod
```

### 2. WebSocket API Gateway URL

This is your WebSocket API Gateway endpoint for real-time updates.

```javascript
WEBSOCKET_API_URL: 'wss://YOUR_WEBSOCKET_API_ID.execute-api.YOUR_REGION.amazonaws.com/YOUR_STAGE'
```

**How to find it:**
1. Go to AWS Console → API Gateway
2. Select your WebSocket API
3. Click "Stages" in the left menu
4. Select your stage (e.g., "prod")
5. Copy the "WebSocket URL" (starts with `wss://`)

**Example:**
```
wss://xyz789abc1.execute-api.us-east-1.amazonaws.com/prod
```

### 3. AWS Region

The AWS region where your services are deployed.

```javascript
AWS_REGION: 'YOUR_REGION'
```

**Common regions:**
- `us-east-1` - US East (N. Virginia)
- `us-west-2` - US West (Oregon)
- `eu-west-1` - Europe (Ireland)
- `ap-southeast-1` - Asia Pacific (Singapore)

### 4. Cognito Configuration (Optional)

If using AWS Cognito for authentication:

```javascript
COGNITO: {
  USER_POOL_ID: 'YOUR_USER_POOL_ID',
  CLIENT_ID: 'YOUR_CLIENT_ID',
  REGION: 'YOUR_REGION'
}
```

**How to find Cognito settings:**
1. Go to AWS Console → Cognito
2. Select your User Pool
3. **User Pool ID**: Found on the "General settings" page
4. **Client ID**: Go to "App clients" and copy the "App client id"
5. **Region**: Same as your User Pool region

**Example:**
```javascript
COGNITO: {
  USER_POOL_ID: 'us-east-1_AbCdEfGhI',
  CLIENT_ID: '1a2b3c4d5e6f7g8h9i0j1k2l3m',
  REGION: 'us-east-1'
}
```

## Complete Configuration Example

```javascript
export const API_CONFIG = {
  REST_API_URL: 'https://abc123def4.execute-api.us-east-1.amazonaws.com/prod',
  WEBSOCKET_API_URL: 'wss://xyz789abc1.execute-api.us-east-1.amazonaws.com/prod',
  AWS_REGION: 'us-east-1',
  COGNITO: {
    USER_POOL_ID: 'us-east-1_AbCdEfGhI',
    CLIENT_ID: '1a2b3c4d5e6f7g8h9i0j1k2l3m',
    REGION: 'us-east-1'
  }
}
```

## API Endpoints

The following endpoints are configured in the application:

### REST Endpoints

1. **POST /upload-file**
   - Request presigned URL for file upload
   - Body: `{ token, filename, content_type }`
   - Response: `{ file_id, presign_url, s3_key }`

2. **GET /metadata/{file_id}**
   - Get metadata for specific file
   - Response: File metadata object

3. **GET /files**
   - List all files for current user
   - Response: Array of file metadata objects

### WebSocket Routes

1. **$connect**
   - Establish WebSocket connection
   - Query params: `token`, `file_id` (optional)

2. **$disconnect**
   - Close WebSocket connection

3. **Message format**
   - Receive: `{ type: "FILE_UPDATE", file_id, file_type, thumbnail_url, tags, upload_timestamp }`

## Testing Configuration

### Method 1: Check API Gateway Health

```bash
# Test REST API
curl https://YOUR_REST_API_URL/health

# Test with authentication
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     https://YOUR_REST_API_URL/files
```

### Method 2: Check WebSocket Connection

Use a WebSocket testing tool like:
- Browser extension: "Simple WebSocket Client"
- Online tool: websocket.org/echo.html
- Command line: `wscat -c "wss://YOUR_WEBSOCKET_URL?token=YOUR_TOKEN"`

### Method 3: Frontend Console

1. Open browser Developer Tools (F12)
2. Go to Console tab
3. Check for connection errors when accessing `/upload` page
4. Look for messages like:
   - "WebSocket connected" ✅ Success
   - "WebSocket error" ❌ Check configuration

## CORS Configuration

Your API Gateway must have CORS enabled for the frontend to work:

### REST API CORS Settings
```
Access-Control-Allow-Origin: * (or your specific domain)
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### WebSocket API
WebSocket connections don't use CORS, but ensure your Lambda Authorizer properly validates tokens.

## Common Issues

### Issue: "Failed to fetch" or "Network Error"

**Cause:** Incorrect REST API URL or CORS not configured

**Solution:**
1. Verify REST_API_URL is correct
2. Check API Gateway CORS settings
3. Test API endpoint with curl

### Issue: WebSocket connection fails immediately

**Cause:** Incorrect WebSocket URL or token issues

**Solution:**
1. Verify WEBSOCKET_API_URL uses `wss://` protocol
2. Check JWT token is valid
3. Review Lambda Authorizer logs in CloudWatch

### Issue: "401 Unauthorized"

**Cause:** Invalid or expired JWT token

**Solution:**
1. Check token expiration time
2. Verify token format (should have 3 parts separated by dots)
3. Test with a newly generated token

### Issue: Uploads fail with 403

**Cause:** Presigned URL issues or S3 permissions

**Solution:**
1. Check Lambda has permission to generate presigned URLs
2. Verify S3 bucket CORS configuration
3. Check presigned URL expiration time

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use HTTPS/WSS** for all connections (not HTTP/WS)
3. **Implement token refresh** for long sessions
4. **Set appropriate CORS policies** (avoid wildcard * in production)
5. **Use short-lived presigned URLs** (recommend 15-60 minutes)
6. **Enable CloudWatch logging** for debugging

## Environment-Specific Configuration

You can create different configurations for different environments:

```javascript
const ENV = import.meta.env.MODE // 'development' or 'production'

const configs = {
  development: {
    REST_API_URL: 'https://dev-api.example.com',
    WEBSOCKET_API_URL: 'wss://dev-ws.example.com',
    AWS_REGION: 'us-east-1'
  },
  production: {
    REST_API_URL: 'https://api.example.com',
    WEBSOCKET_API_URL: 'wss://ws.example.com',
    AWS_REGION: 'us-east-1'
  }
}

export const API_CONFIG = configs[ENV]
```

## Validation Checklist

Before deploying, verify:

- [ ] REST_API_URL is accessible and returns expected responses
- [ ] WEBSOCKET_API_URL can establish connections
- [ ] AWS_REGION matches your backend deployment
- [ ] Cognito configuration (if used) is correct
- [ ] CORS is properly configured on API Gateway
- [ ] JWT tokens are being generated and validated correctly
- [ ] S3 presigned URLs are being generated successfully
- [ ] WebSocket messages are being received
- [ ] All Lambda functions have correct environment variables

## Need Help?

If configuration issues persist:

1. Check AWS CloudWatch Logs for Lambda errors
2. Review API Gateway execution logs
3. Test each component independently
4. Refer to `常见问题解决.md` for common problems
5. Verify all backend infrastructure is deployed correctly

