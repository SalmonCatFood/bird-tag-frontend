/**
 * API Service for backend communication
 * Handles REST API calls to AWS API Gateway
 */

import axios from 'axios'
import config from '@/config'
import authService from './authService'

class ApiService {
  constructor() {
    this.api = axios.create({
      baseURL: config.restApiUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      async (config) => {
        try {
          const session = await authService.getUserSession()
          config.headers['Authorization'] = `Bearer ${session.idToken}`
        } catch {
          // Try stored token from OAuth
          const token = authService.getStoredToken()
          if (token) {
            config.headers['Authorization'] = `Bearer ${token}`
          }
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Unauthorized - redirect to login
          authService.globalSignOut()
        }
        return Promise.reject(error)
      }
    )
  }

  /**
   * Request upload URL from backend
   * @param {string} filename
   * @param {string} contentType
   * @returns {Promise<{file_id: string, presign_url: string, s3_key: string}>}
   */
  async requestUpload(filename, contentType) {
    try {
      const response = await this.api.post('/upload-file', {
        filename,
        content_type: contentType,
      })
      return response.data
    } catch (error) {
      console.error('Request upload error:', error)
      throw error
    }
  }

  /**
   * Upload file to S3 using presigned URL
   * @param {string} presignUrl
   * @param {File} file
   * @param {function} onProgress - Progress callback
   * @returns {Promise<void>}
   */
  async uploadToS3(presignUrl, file, onProgress) {
    try {
      await axios.put(presignUrl, file, {
        headers: {
          'Content-Type': file.type,
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
            onProgress(percentCompleted)
          }
        },
      })
    } catch (error) {
      console.error('Upload to S3 error:', error)
      throw error
    }
  }

  /**
   * Get file metadata
   * @param {string} fileId
   * @returns {Promise<object>}
   */
  async getFileMetadata(fileId) {
    try {
      const response = await this.api.get(`/metadata/${fileId}`)
      return response.data
    } catch (error) {
      console.error('Get metadata error:', error)
      throw error
    }
  }

  /**
   * List user's files
   * @param {object} params - Query parameters
   * @returns {Promise<Array>}
   */
  async listFiles(params = {}) {
    try {
      const response = await this.api.get('/files', { params })
      return response.data
    } catch (error) {
      console.error('List files error:', error)
      throw error
    }
  }
}

export default new ApiService()

