/**
 * Application Configuration
 * All configuration values are loaded from environment variables
 */

export const config = {
  // API Gateway URLs
  restApiUrl: import.meta.env.VITE_REST_API_URL || '',
  websocketApiUrl: import.meta.env.VITE_WEBSOCKET_API_URL || '',
  
  // AWS Cognito Configuration
  cognito: {
    userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
    clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
    region: import.meta.env.VITE_COGNITO_REGION || '',
    clientSecret: import.meta.env.VITE_COGNITO_CLIENT_SECRET || '',
    domain: import.meta.env.VITE_COGNITO_DOMAIN || '',
    redirectSignIn: import.meta.env.VITE_COGNITO_REDIRECT_SIGN_IN || 'http://localhost:5173/auth',
    redirectSignOut: import.meta.env.VITE_COGNITO_REDIRECT_SIGN_OUT || 'http://localhost:5173/auth',
  },
  
  // OAuth Configuration
  oauth: {
    scope: ['openid', 'email', 'profile'],
    responseType: 'code',
  },
}

export default config

