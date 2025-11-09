/**
 * AWS Cognito Authentication Service
 * Handles user authentication with Cognito and Google OAuth
 */

import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
} from 'amazon-cognito-identity-js'
import config from '@/config'

class AuthService {
  constructor() {
    this.userPool = new CognitoUserPool({
      UserPoolId: config.cognito.userPoolId,
      ClientId: config.cognito.clientId,
    })
    this.currentUser = null
  }

  /**
   * Get current authenticated user
   * @returns {CognitoUser|null}
   */
  getCurrentUser() {
    return this.userPool.getCurrentUser()
  }

  /**
   * Decode JWT token payload (without verification)
   * @param {string} token
   * @returns {object}
   */
  decodeJWT(token) {
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
      return JSON.parse(jsonPayload)
    } catch (error) {
      console.error('Failed to decode JWT:', error)
      return null
    }
  }

  /**
   * Get user session and JWT token
   * Supports both Cognito SDK sessions and OAuth tokens from localStorage
   * @returns {Promise<{idToken: string, accessToken: string, refreshToken: string, user: object}>}
   */
  getUserSession() {
    return new Promise((resolve, reject) => {
      // First, try to get session from Cognito SDK (standard login)
      const cognitoUser = this.getCurrentUser()
      
      if (cognitoUser) {
        cognitoUser.getSession((err, session) => {
          if (err) {
            // If Cognito session fails, fall back to OAuth tokens
            return this.getOAuthSession().then(resolve).catch(reject)
          }

          if (!session.isValid()) {
            // If session is invalid, fall back to OAuth tokens
            return this.getOAuthSession().then(resolve).catch(reject)
          }

          cognitoUser.getUserAttributes((err, attributes) => {
            if (err) {
              // If getting attributes fails, fall back to OAuth tokens
              return this.getOAuthSession().then(resolve).catch(reject)
            }

            const userAttributes = {}
            attributes.forEach(attr => {
              userAttributes[attr.Name] = attr.Value
            })

            resolve({
              idToken: session.getIdToken().getJwtToken(),
              accessToken: session.getAccessToken().getJwtToken(),
              refreshToken: session.getRefreshToken().getToken(),
              user: {
                userId: userAttributes['sub'],
                email: userAttributes['email'],
                name: userAttributes['name'] || userAttributes['email'],
                ...userAttributes,
              },
            })
          })
        })
      } else {
        // No Cognito user, try OAuth tokens from localStorage
        this.getOAuthSession().then(resolve).catch(reject)
      }
    })
  }

  /**
   * Get session from OAuth tokens stored in localStorage
   * @returns {Promise<{idToken: string, accessToken: string, refreshToken: string, user: object}>}
   */
  getOAuthSession() {
    return new Promise((resolve, reject) => {
      const idToken = localStorage.getItem('idToken')
      const accessToken = localStorage.getItem('accessToken')
      const refreshToken = localStorage.getItem('refreshToken')

      if (!idToken || !accessToken) {
        reject(new Error('No user found'))
        return
      }

      // Decode JWT to get user information
      const tokenPayload = this.decodeJWT(idToken)
      if (!tokenPayload) {
        reject(new Error('Invalid token'))
        return
      }

      // Check if token is expired
      const now = Math.floor(Date.now() / 1000)
      if (tokenPayload.exp && tokenPayload.exp < now) {
        reject(new Error('Token expired'))
        return
      }

      resolve({
        idToken: idToken,
        accessToken: accessToken,
        refreshToken: refreshToken || '',
        user: {
          userId: tokenPayload.sub || tokenPayload['cognito:username'],
          email: tokenPayload.email || tokenPayload['email'],
          name: tokenPayload.name || tokenPayload['cognito:username'] || tokenPayload.email || 'User',
          ...tokenPayload,
        },
      })
    })
  }

  /**
   * Sign in with username and password
   * @param {string} username
   * @param {string} password
   * @returns {Promise<object>}
   */
  signIn(username, password) {
    return new Promise((resolve, reject) => {
      const authenticationDetails = new AuthenticationDetails({
        Username: username,
        Password: password,
      })

      const cognitoUser = new CognitoUser({
        Username: username,
        Pool: this.userPool,
      })

      cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (result) => {
          this.currentUser = cognitoUser
          resolve({
            idToken: result.getIdToken().getJwtToken(),
            accessToken: result.getAccessToken().getJwtToken(),
            refreshToken: result.getRefreshToken().getToken(),
          })
        },
        onFailure: (err) => {
          reject(err)
        },
      })
    })
  }

  /**
   * Sign up new user
   * @param {string} email
   * @param {string} password
   * @param {object} attributes
   * @returns {Promise<object>}
   */
  signUp(email, password, attributes = {}) {
    return new Promise((resolve, reject) => {
      const attributeList = Object.keys(attributes).map(key => ({
        Name: key,
        Value: attributes[key],
      }))

      this.userPool.signUp(email, password, attributeList, null, (err, result) => {
        if (err) {
          reject(err)
          return
        }
        resolve(result)
      })
    })
  }

  /**
   * Sign out current user
   */
  signOut() {
    const cognitoUser = this.getCurrentUser()
    if (cognitoUser) {
      cognitoUser.signOut()
    }
    this.currentUser = null
  }

  /**
   * Sign in with Google OAuth (Cognito Hosted UI)
   */
  signInWithGoogle() {
    const { domain, clientId, redirectSignIn } = config.cognito
    const { scope, responseType } = config.oauth
    
    const oauthUrl = `${domain}/oauth2/authorize?` + 
      `client_id=${clientId}&` +
      `response_type=${responseType}&` +
      `scope=${encodeURIComponent(scope.join(' '))}&` +
      `redirect_uri=${encodeURIComponent(redirectSignIn)}&` +
      `identity_provider=Google`
    
    window.location.href = oauthUrl
  }

  /**
   * Handle OAuth callback and exchange code for tokens
   * @param {string} code - Authorization code from OAuth callback
   * @returns {Promise<object>}
   */
  async handleOAuthCallback(code) {
    const { domain, clientId, clientSecret, redirectSignIn } = config.cognito
    
    const tokenUrl = `${domain}/oauth2/token`
    
    const params = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: clientId,
      code: code,
      redirect_uri: redirectSignIn,
    })

    // Add client_secret if it exists (for confidential clients)
    // For public clients, don't include client_secret
    const headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    if (clientSecret) {
      // For confidential clients, add to body instead of header
      params.append('client_secret', clientSecret)
    }

    try {
      const response = await fetch(tokenUrl, {
        method: 'POST',
        headers: headers,
        body: params.toString(),
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage = 'Failed to exchange code for tokens'
        try {
          const errorJson = JSON.parse(errorText)
          errorMessage = errorJson.error_description || errorJson.error || errorMessage
        } catch {
          errorMessage = errorText || errorMessage
        }
        console.error('Token exchange error:', errorMessage)
        throw new Error(errorMessage)
      }

      const tokens = await response.json()
      
      // Store tokens in localStorage (you may want to use a more secure method)
      localStorage.setItem('idToken', tokens.id_token)
      localStorage.setItem('accessToken', tokens.access_token)
      if (tokens.refresh_token) {
        localStorage.setItem('refreshToken', tokens.refresh_token)
      }
      
      return tokens
    } catch (error) {
      console.error('OAuth callback error:', error)
      throw error
    }
  }

  /**
   * Get stored JWT token
   * @returns {string|null}
   */
  getStoredToken() {
    return localStorage.getItem('idToken')
  }

  /**
   * Check if user is authenticated
   * @returns {Promise<boolean>}
   */
  async isAuthenticated() {
    try {
      // Try to get session from Cognito
      await this.getUserSession()
      return true
    } catch {
      // Try to check stored token from OAuth
      const token = this.getStoredToken()
      return !!token
    }
  }

  /**
   * Sign out and redirect to Cognito logout
   */
  globalSignOut() {
    const { domain, clientId, redirectSignOut } = config.cognito
    
    // Clear local storage
    localStorage.removeItem('idToken')
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    
    // Sign out from Cognito
    this.signOut()
    
    // Redirect to Cognito logout endpoint
    const logoutUrl = `${domain}/logout?` +
      `client_id=${clientId}&` +
      `logout_uri=${encodeURIComponent(redirectSignOut)}`
    
    window.location.href = logoutUrl
  }
}

export default new AuthService()

