// Cognito 配置
// 从环境变量中读取配置

// 清理 domain 值，移除可能的协议前缀和尾部斜杠
// 支持两种格式：
// 1. 域名前缀：your-domain（会构建为 your-domain.auth.region.amazoncognito.com）
// 2. 完整域名：your-domain.auth.region.amazoncognito.com（直接使用）
function cleanDomain(domain) {
  if (!domain) return ''
  // 移除 https:// 或 http:// 前缀
  domain = domain.replace(/^https?:\/\//, '')
  // 移除尾部斜杠和路径
  domain = domain.split('/')[0]
  return domain
}

// 获取规范化的完整域名
// 如果 domain 已经是完整格式，直接返回；否则构建完整域名
export function getFullDomain(domain, region) {
  if (!domain) return ''
  
  // 检查是否已经是完整域名格式（包含 .auth. 和 .amazoncognito.com）
  if (domain.includes('.auth.') && domain.includes('.amazoncognito.com')) {
    return domain
  }
  
  // 否则构建完整域名
  return `${domain}.auth.${region}.amazoncognito.com`
}

export const COGNITO_CONFIG = {
  // Cognito User Pool ID
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
  
  // Cognito App Client ID
  clientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
  
  // Cognito App Client Secret（可选，如果 App Client 配置需要）
  // 注意：在客户端应用中存储 Client Secret 存在安全风险，建议使用公共客户端
  // 或者在后端处理 token 交换
  clientSecret: import.meta.env.VITE_COGNITO_CLIENT_SECRET || '',
  
  // AWS 区域
  region: import.meta.env.VITE_COGNITO_REGION || 'ap-southeast-2',
  
  // Cognito Domain（用于 Hosted UI），自动清理协议前缀
  domain: cleanDomain(import.meta.env.VITE_COGNITO_DOMAIN || ''),
  
  // OAuth 回调 URL
  redirectSignIn: import.meta.env.VITE_COGNITO_REDIRECT_SIGN_IN || `${window.location.origin}/auth/callback`,
  redirectSignOut: import.meta.env.VITE_COGNITO_REDIRECT_SIGN_OUT || `${window.location.origin}/login`,
  
  // OAuth 作用域
  scope: ['email', 'profile', 'openid'],
  
  // OAuth 响应类型
  responseType: 'code'
}

// 验证配置是否完整
export function validateCognitoConfig() {
  const required = ['userPoolId', 'clientId', 'region']
  const missing = required.filter(key => !COGNITO_CONFIG[key])
  
  if (missing.length > 0) {
    console.warn(`Cognito 配置缺少以下参数: ${missing.join(', ')}`)
    return false
  }
  
  return true
}

// 获取 Cognito Hosted UI URL
export function getHostedUIUrl(state = '') {
  if (!COGNITO_CONFIG.domain) {
    throw new Error('Cognito Domain 未配置')
  }
  
  const fullDomain = getFullDomain(COGNITO_CONFIG.domain, COGNITO_CONFIG.region)
  
  const params = new URLSearchParams({
    client_id: COGNITO_CONFIG.clientId,
    response_type: COGNITO_CONFIG.responseType,
    scope: COGNITO_CONFIG.scope.join(' '),
    redirect_uri: COGNITO_CONFIG.redirectSignIn
  })
  
  if (state) {
    params.append('state', state)
  }
  
  return `https://${fullDomain}/oauth2/authorize?${params.toString()}`
}

// 获取 Google OAuth URL（通过 Cognito）
export function getGoogleOAuthUrl(state = '') {
  if (!COGNITO_CONFIG.domain) {
    throw new Error('Cognito Domain 未配置')
  }
  
  const fullDomain = getFullDomain(COGNITO_CONFIG.domain, COGNITO_CONFIG.region)
  
  const params = new URLSearchParams({
    client_id: COGNITO_CONFIG.clientId,
    response_type: COGNITO_CONFIG.responseType,
    scope: COGNITO_CONFIG.scope.join(' '),
    redirect_uri: COGNITO_CONFIG.redirectSignIn,
    identity_provider: 'Google'
  })
  
  if (state) {
    params.append('state', state)
  }
  
  return `https://${fullDomain}/oauth2/authorize?${params.toString()}`
}

