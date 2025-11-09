# BirdTag Frontend - Quick Start Guide

## Prerequisites

- Node.js 20.19.0 or 22.12.0+
- npm or yarn package manager
- AWS backend services deployed (optional for development)

## Installation

1. **Navigate to project directory**:
   ```bash
   cd birdtag
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure API endpoints** (Required for production):
   
   Edit `src/config/api.js` and update:
   - `REST_API_URL` - Your REST API Gateway URL
   - `WEBSOCKET_API_URL` - Your WebSocket API Gateway URL
   - `AWS_REGION` - Your AWS region
   - Cognito settings (if using Cognito authentication)

## Running the Application

### Development Mode

```bash
npm run dev
```

The application will start at `http://localhost:5173`

### Production Build

```bash
npm run build
```

Build output will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Default Routes

- `/` - Redirects to login
- `/login` - Login page (uses mock authentication currently)
- `/upload` - File upload interface (requires authentication)
- `/files` - File listing and management (requires authentication)

## Mock Authentication

For development without backend, use any username/password combination:

- Username: `demo`
- Password: `demo123`

The application will generate a mock JWT token and allow access to protected routes.

## Project Structure

```
birdtag/
├── src/
│   ├── config/          # API configuration
│   ├── utils/           # Utility functions
│   ├── services/        # API and WebSocket services
│   ├── views/           # Page components
│   └── router/          # Route configuration
├── public/              # Static assets
└── note/                # Documentation
```

## Key Features

1. **Authentication**: Login/logout with JWT token management
2. **File Upload**: Drag-drop or browse to upload files
3. **Real-time Updates**: WebSocket connection for live processing status
4. **File Management**: View, filter, and manage uploaded files

## Development Notes

- Mock data is used when backend is not configured
- WebSocket connection will fail gracefully if backend is unavailable
- File uploads require valid backend endpoints

## Next Steps

1. Configure AWS backend endpoints in `src/config/api.js`
2. Implement Cognito authentication (see `Frontend-Development-Guide.md`)
3. Test file upload flow with actual backend
4. Customize UI/UX as needed

## Troubleshooting

**Port already in use**: Change port in `vite.config.js` or kill process using port 5173

**Cannot resolve dependencies**: Delete `node_modules` and `package-lock.json`, then run `npm install`

**WebSocket errors in console**: Normal if backend is not configured, app will work in limited mode

## Documentation

- `Frontend-Development-Guide.md` - Comprehensive development guide
- `项目提示词.md` - Complete project architecture and backend details
- `常见问题解决.md` - Common issues and solutions

## Support

For issues or questions, refer to the documentation in the `note/` directory.

