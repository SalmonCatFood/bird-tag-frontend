import { WEBSOCKET_API_URL } from '@/config/api'
import { getToken, getUserIdFromToken } from '@/utils/auth'

/**
 * WebSocket 连接管理服务
 */
class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
    this.fileId = null
  }

  /**
   * 连接到 WebSocket
   * @param {string} fileId - 文件 ID
   * @param {Function} onMessage - 消息回调
   * @param {Function} onError - 错误回调
   * @param {Function} onClose - 关闭回调
   */
  connect(fileId, onMessage, onError, onClose) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    this.fileId = fileId
    const token = getToken()
    
    if (!token) {
      console.error('No token available for WebSocket connection')
      if (onError) onError(new Error('No authentication token'))
      return
    }

    // 构建 WebSocket URL，包含 token 和 file_id 作为查询参数
    const url = `${WEBSOCKET_API_URL}?token=${encodeURIComponent(token)}&file_id=${encodeURIComponent(fileId)}`
    
    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        if (onMessage) {
          this.addMessageListener(onMessage)
        }
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.notifyListeners(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        if (onError) onError(error)
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket closed', event.code, event.reason)
        this.ws = null
        
        // 如果不是正常关闭，尝试重连
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          setTimeout(() => {
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
            this.connect(this.fileId, onMessage, onError, onClose)
          }, this.reconnectDelay * this.reconnectAttempts)
        } else if (onClose) {
          onClose(event)
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      if (onError) onError(error)
    }
  }

  /**
   * 添加消息监听器
   * @param {Function} listener - 监听函数
   * @returns {Function} - 取消监听的函数
   */
  addMessageListener(listener) {
    const id = Date.now() + Math.random()
    this.listeners.set(id, listener)
    return () => this.listeners.delete(id)
  }

  /**
   * 通知所有监听器
   * @param {object} data - 消息数据
   */
  notifyListeners(data) {
    this.listeners.forEach((listener) => {
      try {
        listener(data)
      } catch (error) {
        console.error('Error in WebSocket listener:', error)
      }
    })
  }

  /**
   * 发送消息（如果需要）
   * @param {object} data - 要发送的数据
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this.listeners.clear()
    this.fileId = null
  }

  /**
   * 检查连接状态
   * @returns {boolean}
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
}

// 导出单例
export default new WebSocketService()

