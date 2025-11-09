# BirdTag Frontend - File Structure Reference

## Complete File Listing

```
birdtag/
├── src/
│   ├── config/
│   │   └── api.js                    # API configuration and endpoints
│   │
│   ├── utils/
│   │   └── auth.js                   # Authentication utilities
│   │
│   ├── services/
│   │   ├── api.js                    # REST API service
│   │   └── websocket.js              # WebSocket service
│   │
│   ├── views/
│   │   ├── Login.vue                 # Login page component
│   │   ├── Upload.vue                # File upload interface
│   │   └── FileList.vue              # File listing and management
│   │
│   ├── router/
│   │   └── index.js                  # Vue Router configuration
│   │
│   ├── App.vue                       # Main application component
│   └── main.js                       # Application entry point
│
├── public/
│   └── favicon.ico                   # Application favicon
│
├── note/
│   ├── API-Configuration.md          # API configuration guide
│   ├── Frontend-Development-Guide.md # Comprehensive dev guide
│   ├── Quick-Start.md                # Quick start instructions
│   ├── Project-File-Structure.md     # This file
│   ├── Cognito配置说明.md            # Cognito setup (Chinese)
│   ├── 常见问题解决.md               # Common issues (Chinese)
│   └── 项目提示词.md                 # Project architecture (Chinese)
│
├── package.json                      # Project dependencies
├── package-lock.json                 # Locked dependencies
├── vite.config.js                    # Vite configuration
├── jsconfig.json                     # JavaScript configuration
├── index.html                        # HTML entry point
├── .gitignore                        # Git ignore rules
└── README.md                         # Project readme

```

## File Descriptions

### Source Files (`src/`)

#### Configuration (`src/config/`)

**`api.js`** - Central API configuration
- REST API Gateway URL
- WebSocket API Gateway URL
- AWS region settings
- Cognito configuration
- API endpoint definitions

**Key exports:**
- `API_CONFIG` - Main configuration object
- `API_ENDPOINTS` - Endpoint paths

---

#### Utilities (`src/utils/`)

**`auth.js`** - Authentication helper functions
- Token storage and retrieval
- Token validation and parsing
- User information management
- JWT decoding utilities

**Key functions:**
- `setToken(token)` - Store auth token
- `getToken()` - Retrieve auth token
- `isAuthenticated()` - Check auth status
- `parseJWT(token)` - Parse JWT payload
- `getUserIdFromToken()` - Extract user ID

---

#### Services (`src/services/`)

**`api.js`** - REST API service layer
- HTTP request handling
- Authentication headers
- File upload management
- Metadata operations

**Key functions:**
- `requestUploadUrl(filename, contentType)` - Get presigned URL
- `uploadFileToS3(presignUrl, file, onProgress)` - Upload to S3
- `getFileMetadata(fileId)` - Fetch file metadata
- `listFiles()` - List user files

**`websocket.js`** - WebSocket connection manager
- Singleton WebSocket instance
- Connection lifecycle management
- Automatic reconnection
- Message handler registration

**Key methods:**
- `connect(fileId)` - Establish connection
- `disconnect()` - Close connection
- `onMessage(handler)` - Subscribe to messages
- `send(data)` - Send message to server

---

#### Views (`src/views/`)

**`Login.vue`** - Authentication page
- Username/password form
- JWT token handling
- Mock authentication (dev mode)
- Redirect after login

**Features:**
- Form validation
- Loading states
- Error handling
- Responsive design

**`Upload.vue`** - File upload interface
- Drag-and-drop zone
- Multiple file support
- Upload progress tracking
- Real-time status updates

**Features:**
- File type detection
- Progress bars
- WebSocket integration
- Processing notifications
- Tag display

**`FileList.vue`** - File management page
- Grid layout display
- File type filtering
- Thumbnail previews
- Tag visualization

**Features:**
- Responsive grid
- Type filters (all/image/video/audio)
- Refresh capability
- Original file links
- Mock data support (dev mode)

---

#### Router (`src/router/`)

**`index.js`** - Vue Router configuration
- Route definitions
- Navigation guards
- Authentication protection
- Route redirects

**Routes:**
- `/` - Redirect to login
- `/login` - Login page
- `/upload` - Upload interface (protected)
- `/files` - File listing (protected)

---

#### Core Files

**`App.vue`** - Main application component
- Top navigation bar
- User information display
- Logout functionality
- Router view container
- Global styles

**`main.js`** - Application entry point
- Vue app initialization
- Router integration
- App mounting

---

### Documentation (`note/`)

**English Documentation:**

1. **`API-Configuration.md`**
   - Complete API setup guide
   - Configuration parameters
   - Testing procedures
   - Troubleshooting

2. **`Frontend-Development-Guide.md`**
   - Comprehensive development guide
   - Architecture overview
   - Component details
   - Integration instructions
   - Best practices

3. **`Quick-Start.md`**
   - Installation steps
   - Running the app
   - Default routes
   - Mock authentication

4. **`Project-File-Structure.md`** (This file)
   - Complete file listing
   - File descriptions
   - Usage guidelines

**Chinese Documentation:**

5. **`Cognito配置说明.md`**
   - AWS Cognito setup (Chinese)

6. **`常见问题解决.md`**
   - Common issues and solutions (Chinese)

7. **`项目提示词.md`**
   - Complete project architecture
   - Backend details
   - Data flow
   - Lambda code samples

---

### Configuration Files

**`package.json`**
- Project metadata
- Dependencies:
  - `vue` ^3.5.22
  - `vue-router` ^4.6.3
  - `aws-amplify` ^6.15.7
  - `amazon-cognito-identity-js` ^6.3.15
- Scripts:
  - `dev` - Development server
  - `build` - Production build
  - `preview` - Preview build

**`vite.config.js`**
- Vite build configuration
- Vue plugin setup
- Dev server settings
- Build optimizations

**`jsconfig.json`**
- JavaScript/TypeScript configuration
- Path aliases
- IDE support

**`index.html`**
- HTML entry point
- App mounting div
- Meta tags

**`.gitignore`**
- Version control exclusions
- `node_modules/`
- `dist/`
- `.env` files

---

## File Dependencies

### Import Chain

```
main.js
  └── App.vue
      ├── router/index.js
      │   ├── utils/auth.js
      │   ├── views/Login.vue
      │   ├── views/Upload.vue
      │   │   ├── services/api.js
      │   │   │   └── config/api.js
      │   │   │   └── utils/auth.js
      │   │   └── services/websocket.js
      │   │       └── config/api.js
      │   │       └── utils/auth.js
      │   └── views/FileList.vue
      │       └── services/api.js
      └── utils/auth.js
```

### External Dependencies

- **Vue 3** - Core framework
- **Vue Router 4** - Routing
- **AWS Amplify** - AWS service integration (ready)
- **Cognito Identity JS** - Authentication (ready)
- **Vite** - Build tool

---

## File Size Reference

| File | Lines | Purpose |
|------|-------|---------|
| `config/api.js` | ~30 | Configuration |
| `utils/auth.js` | ~90 | Auth utilities |
| `services/api.js` | ~100 | REST API |
| `services/websocket.js` | ~150 | WebSocket |
| `views/Login.vue` | ~200 | Login UI |
| `views/Upload.vue` | ~400 | Upload UI |
| `views/FileList.vue` | ~450 | File list UI |
| `router/index.js` | ~50 | Routing |
| `App.vue` | ~170 | Main app |
| `main.js` | ~10 | Entry |

**Total LOC:** ~1,650 lines

---

## Modification Guidelines

### When to edit each file:

**`config/api.js`**
- ✅ When setting up API endpoints
- ✅ When configuring AWS services
- ❌ Don't add business logic here

**`utils/auth.js`**
- ✅ When adding auth utilities
- ✅ When changing token storage
- ❌ Don't add API calls here

**`services/api.js`**
- ✅ When adding new API endpoints
- ✅ When modifying request logic
- ❌ Don't add UI logic here

**`services/websocket.js`**
- ✅ When modifying WebSocket behavior
- ✅ When adding connection features
- ❌ Don't add business logic here

**`views/*.vue`**
- ✅ When modifying UI/UX
- ✅ When adding page features
- ✅ When styling components
- ❌ Don't add service logic here

**`router/index.js`**
- ✅ When adding new routes
- ✅ When modifying guards
- ❌ Don't add component logic here

**`App.vue`**
- ✅ When modifying global layout
- ✅ When adding global features
- ❌ Don't add page-specific logic here

---

## Quick Navigation

**Need to configure AWS endpoints?**
→ Edit `src/config/api.js`

**Need to modify login behavior?**
→ Edit `src/views/Login.vue` and `src/utils/auth.js`

**Need to change upload UI?**
→ Edit `src/views/Upload.vue`

**Need to add new API endpoint?**
→ Add to `src/services/api.js`

**Need to modify routes?**
→ Edit `src/router/index.js`

**Need to change global styles?**
→ Edit `src/App.vue` (global styles section)

---

## Next Steps

1. **Configure APIs** - Update `src/config/api.js`
2. **Test locally** - Run `npm run dev`
3. **Connect backend** - Verify API connectivity
4. **Customize UI** - Modify components as needed
5. **Deploy** - Build and deploy to hosting

For detailed instructions, refer to:
- **Setup**: `Quick-Start.md`
- **Configuration**: `API-Configuration.md`
- **Development**: `Frontend-Development-Guide.md`

