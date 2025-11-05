import { REST_API_BASE_URL, API_ENDPOINTS } from '@/config/api'
import { getToken, clearToken, isTokenExpired } from '@/utils/auth'

/**
 * 发送 HTTP 请求
 * @param {string} endpoint - API 端点
 * @param {object} options - fetch 选项
 * @returns {Promise<Response>}
 */
async function request(endpoint, options = {}) {
  const url = `${REST_API_BASE_URL}${endpoint}`
  const token = getToken()

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  }

  // 如果需要认证，添加 token 到请求体（根据后端要求）
  let body = {}
  if (options.body) {
    try {
      body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body
    } catch {
      body = {}
    }
  }
  if (token && !body.token) {
    body.token = token
  }

  const config = {
    ...options,
    headers,
    body: JSON.stringify(body)
  }

  try {
    const response = await fetch(url, config)
    
    // 如果 token 过期，清除并跳转到登录页
    if (response.status === 401) {
      clearToken()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    return response
  } catch (error) {
    console.error('API request failed:', error)
    throw error
  }
}

/**
 * 上传文件请求 - 获取 presigned URL
 * @param {string} filename - 文件名
 * @param {string} contentType - 文件 MIME 类型
 * @returns {Promise<object>} - { file_id, presign_url, s3_key }
 */
export async function requestUploadFile(filename, contentType) {
  const response = await request(API_ENDPOINTS.UPLOAD_FILE, {
    method: 'POST',
    body: JSON.stringify({
      filename,
      content_type: contentType
    })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Upload request failed' }))
    throw new Error(error.error || 'Failed to request upload')
  }

  return await response.json()
}

/**
 * 使用 presigned URL 上传文件到 S3
 * @param {string} presignedUrl - presigned URL
 * @param {File} file - 要上传的文件
 * @param {Function} onProgress - 进度回调 (progress: number) => void
 * @returns {Promise<void>}
 */
export async function uploadToS3(presignedUrl, file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const progress = (e.loaded / e.total) * 100
        onProgress(progress)
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve()
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'))
    })

    xhr.open('PUT', presignedUrl)
    xhr.setRequestHeader('Content-Type', file.type)
    xhr.send(file)
  })
}

/**
 * 获取文件元数据
 * @param {string} fileId - 文件 ID
 * @returns {Promise<object>} - 文件元数据
 */
export async function getFileMetadata(fileId) {
  const response = await request(API_ENDPOINTS.GET_METADATA(fileId), {
    method: 'GET'
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to fetch metadata' }))
    throw new Error(error.error || 'Failed to fetch metadata')
  }

  return await response.json()
}

