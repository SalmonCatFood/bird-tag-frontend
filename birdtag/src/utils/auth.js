// JWT Token 管理工具

/**
 * 从 JWT token 中解析 payload（不验证签名）
 * @param {string} token - JWT token
 * @returns {object|null} - 解析后的 payload，失败返回 null
 */
export function parseJWT(token) {
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
 * 检查 token 是否过期
 * @param {string} token - JWT token
 * @returns {boolean} - true 表示已过期或无效
 */
export function isTokenExpired(token) {
  const payload = parseJWT(token)
  if (!payload || !payload.exp) {
    return true
  }
  return Date.now() >= payload.exp * 1000
}

/**
 * 从 token 中获取 user_id
 * @param {string} token - JWT token
 * @returns {string|null} - user_id 或 sub，失败返回 null
 */
export function getUserIdFromToken(token) {
  const payload = parseJWT(token)
  if (!payload) {
    return null
  }
  return payload.user_id || payload.sub || null
}

/**
 * 保存 token 到 localStorage
 * @param {string} idToken - JWT ID Token
 * @param {string} accessToken - Access Token（可选）
 * @param {string} refreshToken - Refresh Token（可选）
 */
export function saveToken(idToken, accessToken = null, refreshToken = null) {
  localStorage.setItem('jwt_token', idToken)
  if (accessToken) {
    localStorage.setItem('access_token', accessToken)
  }
  if (refreshToken) {
    localStorage.setItem('refresh_token', refreshToken)
  }
}

/**
 * 从 localStorage 获取 token
 * @returns {string|null}
 */
export function getToken() {
  return localStorage.getItem('jwt_token')
}

/**
 * 获取 Access Token
 * @returns {string|null}
 */
export function getAccessToken() {
  return localStorage.getItem('access_token')
}

/**
 * 获取 Refresh Token
 * @returns {string|null}
 */
export function getRefreshToken() {
  return localStorage.getItem('refresh_token')
}

/**
 * 清除所有 token
 */
export function clearToken() {
  localStorage.removeItem('jwt_token')
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

/**
 * 检查是否已登录
 * @returns {boolean}
 */
export function isAuthenticated() {
  const token = getToken()
  if (!token) {
    return false
  }
  return !isTokenExpired(token)
}

