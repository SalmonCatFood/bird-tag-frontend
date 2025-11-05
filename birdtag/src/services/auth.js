import { CognitoIdentityProviderClient, InitiateAuthCommand, AuthFlowType, GetUserCommand, GlobalSignOutCommand } from '@aws-sdk/client-cognito-identity-provider'
import { COGNITO_CONFIG, getGoogleOAuthUrl as getCognitoGoogleOAuthUrl, getFullDomain } from '@/config/cognito'
import { saveToken, clearToken, getToken, getAccessToken } from '@/utils/auth'

// 创建 Cognito 客户端
const cognitoClient = new CognitoIdentityProviderClient({
  region: COGNITO_CONFIG.region
})

/**
 * 使用用户名和密码登录
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise<{ idToken: string, accessToken: string, refreshToken: string }>}
 */
export async function loginWithPassword(username, password) {
  try {
    const command = new InitiateAuthCommand({
      AuthFlow: AuthFlowType.USER_PASSWORD_AUTH,
      ClientId: COGNITO_CONFIG.clientId,
      AuthParameters: {
        USERNAME: username,
        PASSWORD: password
      }
    })

    const response = await cognitoClient.send(command)

    if (!response.AuthenticationResult) {
      throw new Error('登录失败：未收到认证结果')
    }

    const { IdToken, AccessToken, RefreshToken } = response.AuthenticationResult

    if (!IdToken) {
      throw new Error('登录失败：未收到 ID Token')
    }

    // 保存所有 token
    saveToken(IdToken, AccessToken, RefreshToken)

    return {
      idToken: IdToken,
      accessToken: AccessToken,
      refreshToken: RefreshToken
    }
  } catch (error) {
    console.error('Cognito 登录错误:', error)
    
    // 处理常见错误
    if (error.name === 'NotAuthorizedException') {
      throw new Error('用户名或密码错误')
    } else if (error.name === 'UserNotConfirmedException') {
      throw new Error('用户未确认，请检查邮箱')
    } else if (error.name === 'UserNotFoundException') {
      throw new Error('用户不存在')
    } else if (error.name === 'TooManyRequestsException') {
      throw new Error('请求过于频繁，请稍后再试')
    }
    
    throw new Error(error.message || '登录失败')
  }
}

/**
 * 使用 Google OAuth 登录（重定向到 Cognito Hosted UI）
 */
export function loginWithGoogle() {
  try {
    const state = generateState()
    sessionStorage.setItem('oauth_state', state)
    
    // 使用 cognito.js 中导出的函数
    const googleOAuthUrl = getCognitoGoogleOAuthUrl(state)
    window.location.href = googleOAuthUrl
  } catch (error) {
    console.error('Google OAuth 登录错误:', error)
    throw new Error(error.message || 'Google 登录失败')
  }
}

/**
 * 处理 OAuth 回调（从 URL 中提取 code 并交换 token）
 * @param {string} code - 授权码
 * @returns {Promise<{ idToken: string, accessToken: string, refreshToken: string }>}
 */
export async function handleOAuthCallback(code) {
  try {
    // 获取完整域名（如果 domain 已经是完整格式则直接使用）
    const fullDomain = getFullDomain(COGNITO_CONFIG.domain, COGNITO_CONFIG.region)
    
    // 构建 token 交换 URL
    const tokenUrl = `https://${fullDomain}/oauth2/token`
    
    const params = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: COGNITO_CONFIG.clientId,
      code: code,
      redirect_uri: COGNITO_CONFIG.redirectSignIn
    })

    // 如果配置了 Client Secret，添加到请求参数中
    if (COGNITO_CONFIG.clientSecret) {
      params.append('client_secret', COGNITO_CONFIG.clientSecret)
    }

    // 构建请求头
    const headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }

    // 如果配置了 Client Secret，也可以使用 Basic Auth（可选，推荐方式）
    // 这里使用参数方式，如果需要 Basic Auth 可以取消下面的注释
    // if (COGNITO_CONFIG.clientSecret) {
    //   const credentials = btoa(`${COGNITO_CONFIG.clientId}:${COGNITO_CONFIG.clientSecret}`)
    //   headers['Authorization'] = `Basic ${credentials}`
    // }

    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: headers,
      body: params.toString()
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Token 交换失败' }))
      throw new Error(error.error || 'Token 交换失败')
    }

    const data = await response.json()

    if (!data.id_token) {
      throw new Error('未收到 ID Token')
    }

    // 保存所有 token
    saveToken(data.id_token, data.access_token, data.refresh_token)

    return {
      idToken: data.id_token,
      accessToken: data.access_token,
      refreshToken: data.refresh_token
    }
  } catch (error) {
    console.error('OAuth 回调处理错误:', error)
    throw new Error(error.message || 'OAuth 回调处理失败')
  }
}

/**
 * 获取当前用户信息
 * @returns {Promise<object>} - 用户信息
 */
export async function getCurrentUser() {
  try {
    const accessToken = getAccessToken()
    if (!accessToken) {
      // 如果没有 AccessToken，尝试使用 IdToken（虽然不太理想）
      const idToken = getToken()
      if (!idToken) {
        throw new Error('未找到 token')
      }
      // 对于这种情况，我们可以从 IdToken 中解析用户信息
      const payload = parseJWT(idToken)
      return {
        username: payload['cognito:username'] || payload.sub,
        attributes: {
          email: payload.email,
          sub: payload.sub
        }
      }
    }

    const command = new GetUserCommand({
      AccessToken: accessToken
    })

    const response = await cognitoClient.send(command)
    
    return {
      username: response.Username,
      attributes: response.UserAttributes?.reduce((acc, attr) => {
        acc[attr.Name] = attr.Value
        return acc
      }, {}) || {}
    }
  } catch (error) {
    console.error('获取用户信息错误:', error)
    throw error
  }
}

/**
 * 解析 JWT token（辅助函数）
 * @param {string} token - JWT token
 * @returns {object|null}
 */
function parseJWT(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (error) {
    console.error('Failed to parse JWT:', error)
    return null
  }
}

/**
 * 登出
 * 注意：AWS SDK v3 没有 SignOutCommand，这里使用 GlobalSignOutCommand（需要 AccessToken）
 * 如果只需要客户端登出，清除本地 token 即可
 */
export async function logout() {
  try {
    const accessToken = getAccessToken()
    
    // 如果存在 AccessToken，尝试服务器端登出（使 refresh token 失效）
    if (accessToken) {
      try {
        const command = new GlobalSignOutCommand({
          AccessToken: accessToken
        })
        await cognitoClient.send(command)
      } catch (error) {
        // 如果服务器端登出失败，仍然清除本地 token
        console.warn('服务器端登出失败，但仍将清除本地 token:', error)
      }
    }
    
    // 清除本地存储的所有 token
    clearToken()
  } catch (error) {
    console.error('登出错误:', error)
    // 即使出错也清除本地 token
    clearToken()
  }
}

/**
 * 检查认证状态
 * @returns {Promise<boolean>}
 */
export async function checkAuthStatus() {
  const token = getToken()
  if (!token) {
    return false
  }

  try {
    // 可以尝试获取用户信息来验证 token 是否有效
    await getCurrentUser()
    return true
  } catch {
    // Token 无效，清除
    clearToken()
    return false
  }
}

/**
 * 生成 OAuth state 参数（用于防止 CSRF 攻击）
 * @returns {string}
 */
function generateState() {
  const array = new Uint8Array(16)
  crypto.getRandomValues(array)
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('')
}


