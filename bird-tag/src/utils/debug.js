/**
 * Debug utilities
 * Only for development troubleshooting
 */

import config from '@/config'

export function logConfig() {
  console.log('=== Cognito Configuration ===')
  console.log('Domain:', config.cognito.domain)
  console.log('Client ID:', config.cognito.clientId)
  console.log('Redirect Sign In:', config.cognito.redirectSignIn)
  console.log('Redirect Sign Out:', config.cognito.redirectSignOut)
  console.log('Has Client Secret:', !!config.cognito.clientSecret)
  console.log('Client Secret Length:', config.cognito.clientSecret?.length || 0)
  console.log('OAuth Scopes:', config.oauth.scope)
  console.log('OAuth Response Type:', config.oauth.responseType)
  console.log('============================')
}

// Make it available globally for debugging
if (typeof window !== 'undefined') {
  window.debugConfig = logConfig
}

