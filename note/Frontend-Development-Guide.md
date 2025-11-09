# BirdTag Frontend Development Guide

## Overview

This is a Vue 3 based frontend application for the BirdTag wildlife recognition and tagging platform. The application allows users to upload images, videos, and audio files, which are then processed by AWS backend services for automatic species recognition.

## Technology Stack

- **Framework**: Vue 3 (Composition API)
- **Build Tool**: Vite
- **Router**: Vue Router 4
- **State Management**: Vue Reactivity (no Vuex/Pinia required for now)
- **Styling**: Scoped CSS with modern CSS features
- **AWS Integration**: AWS Amplify, Cognito (ready for integration)

## Project Structure

```
birdtag/
├── src/
│   ├── config/
│   │   └── api.js              # API configuration and endpoints
│   ├── utils/
│   │   └── auth.js             # Authentication utilities
│   ├── services/
│   │   ├── api.js              # REST API service
│   │   └── websocket.js        # WebSocket service for real-time updates
│   ├── views/
│   │   ├── Login.vue           # Login page
│   │   ├── Upload.vue          # File upload interface
│   │   └── FileList.vue        # File listing and management
│   ├── router/
│   │   └── index.js            # Route configuration
│   ├── App.vue                 # Main application component
│   └── main.js                 # Application entry point
├── public/
├── package.json
└── vite.config.js
```

## Configuration

### API Endpoints Configuration

Before running the application, you must update the API configuration in `src/config/api.js`:

```javascript
export const API_CONFIG = {
  REST_API_URL: 'https://YOUR_REST_API_ID.execute-api.YOUR_REGION.amazonaws.com/YOUR_STAGE',
  WEBSOCKET_API_URL: 'wss://YOUR_WEBSOCKET_API_ID.execute-api.YOUR_REGION.amazonaws.com/YOUR_STAGE',
  AWS_REGION: 'YOUR_REGION',
  COGNITO: {
    USER_POOL_ID: 'YOUR_USER_POOL_ID',
    CLIENT_ID: 'YOUR_CLIENT_ID',
    REGION: 'YOUR_REGION'
  }
}
```

## Key Features

### 1. Authentication Flow

- User logs in via the Login page
- JWT token is stored in localStorage
- Token is automatically attached to API requests
- Navigation guard protects authenticated routes
- Token expiration is checked automatically

### 2. File Upload Flow

The upload process follows these steps:

1. User selects files via drag-drop or file picker
2. Frontend requests presigned URL from backend (`POST /upload-file`)
3. Backend creates metadata entry in DynamoDB and returns presigned S3 URL
4. Frontend uploads file directly to S3 using presigned URL
5. Frontend establishes WebSocket connection for real-time updates
6. Backend processes file (thumbnail generation, species recognition)
7. Backend updates DynamoDB metadata table
8. DynamoDB Stream triggers notification Lambda
9. Frontend receives real-time updates via WebSocket

### 3. Real-time Updates

- WebSocket connection established after login
- Receives FILE_UPDATE messages when processing completes
- Automatically updates UI with thumbnails and recognition results
- Handles reconnection automatically if connection drops

### 4. File Management

- View all uploaded files in grid layout
- Filter by file type (images, videos, audio)
- Display thumbnails and recognition tags
- Refresh individual file metadata
- View original files on S3

## Component Details

### Login.vue

- Simple username/password form
- Currently uses mock authentication
- TODO: Integrate with AWS Cognito for real authentication
- Redirects to upload page after successful login

### Upload.vue

- Drag-and-drop file upload interface
- Multiple file upload support
- Progress tracking for each upload
- Real-time status updates via WebSocket
- Displays processing status and recognition results

### FileList.vue

- Grid view of all user files
- Filter by file type
- Display thumbnails and metadata
- Show recognition tags with counts
- Link to original files
- Refresh capability for individual files

## API Services

### REST API Service (`services/api.js`)

Functions:
- `requestUploadUrl(filename, contentType)` - Get presigned URL for upload
- `uploadFileToS3(presignUrl, file, onProgress)` - Upload file to S3 with progress
- `getFileMetadata(fileId)` - Get metadata for specific file
- `listFiles()` - List all files for current user

### WebSocket Service (`services/websocket.js`)

Features:
- Singleton pattern for global connection management
- Automatic reconnection with exponential backoff
- Message handler registration/unregistration
- Connection state management
- Token-based authentication

## Authentication Utilities (`utils/auth.js`)

Functions:
- `setToken(token)` - Store authentication token
- `getToken()` - Retrieve stored token
- `removeToken()` - Clear authentication data
- `isAuthenticated()` - Check if user is authenticated
- `parseJWT(token)` - Parse JWT payload
- `getUserIdFromToken()` - Extract user ID from token

## Development

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Backend Integration TODOs

### 1. AWS Cognito Integration

Currently, the login page uses mock authentication. To integrate with AWS Cognito:

1. Update Cognito configuration in `src/config/api.js`
2. Implement actual Cognito authentication in `Login.vue`
3. Use AWS Amplify Auth module:

```javascript
import { Auth } from 'aws-amplify'

// Configure Amplify
Auth.configure({
  region: API_CONFIG.COGNITO.REGION,
  userPoolId: API_CONFIG.COGNITO.USER_POOL_ID,
  userPoolWebClientId: API_CONFIG.COGNITO.CLIENT_ID
})

// Sign in
const user = await Auth.signIn(username, password)
const token = user.signInUserSession.idToken.jwtToken
```

### 2. API Gateway Configuration

Update the following in `src/config/api.js`:

- `REST_API_URL` - Your REST API Gateway endpoint
- `WEBSOCKET_API_URL` - Your WebSocket API Gateway endpoint
- `AWS_REGION` - Your AWS region

### 3. WebSocket Connection

The WebSocket service is ready to connect but requires:

- Valid WebSocket API Gateway URL
- Lambda Authorizer configured on `$connect` route
- Connection handler Lambda to store connection in DynamoDB

### 4. File Listing API

Currently `FileList.vue` uses mock data. To enable real file listing:

1. Implement `GET /files` endpoint in backend
2. Update `listFiles()` function in `services/api.js`
3. Remove mock data generator from `FileList.vue`

## Security Considerations

1. **JWT Token Storage**: Currently using localStorage. Consider using httpOnly cookies for production
2. **Token Refresh**: Implement token refresh mechanism for long sessions
3. **CORS Configuration**: Ensure API Gateway has proper CORS settings
4. **S3 Presigned URLs**: Ensure URLs have appropriate expiration times
5. **WebSocket Authentication**: Token is passed in query string - ensure WSS connection

## Testing Recommendations

1. **Unit Tests**: Add tests for utility functions (auth, parsing, etc.)
2. **Component Tests**: Test individual Vue components
3. **E2E Tests**: Test complete upload and view flows
4. **WebSocket Testing**: Test reconnection and message handling

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Known Limitations

1. No file size validation on frontend (should add)
2. No file type validation beyond MIME type
3. No batch upload cancel functionality
4. No file deletion capability
5. Limited error handling and user feedback
6. No loading states for route transitions

## Future Enhancements

1. Add user profile page
2. Implement file sharing and permissions
3. Add advanced search and filtering
4. Export recognition results
5. Batch operations on files
6. Image/video preview modal
7. Download processed results
8. Statistics dashboard
9. Multi-language support
10. Dark mode

## Troubleshooting

### WebSocket Connection Fails

- Check if WebSocket URL is correct
- Verify token is valid
- Check Lambda Authorizer logs
- Ensure CORS is configured correctly

### File Upload Fails

- Check if presigned URL is valid
- Verify S3 bucket permissions
- Check file size limits
- Review browser console for errors

### Real-time Updates Not Working

- Verify WebSocket connection is established
- Check DynamoDB Streams configuration
- Review MetaDbUpdate Lambda logs
- Ensure CONNECTION_TABLE is being updated

## Contact & Support

For backend integration issues, refer to:
- `项目提示词.md` - Complete backend architecture
- `常见问题解决.md` - Common issues and solutions
- AWS CloudWatch Logs - For Lambda execution errors

