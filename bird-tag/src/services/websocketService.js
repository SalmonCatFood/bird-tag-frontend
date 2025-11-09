/**
 * WebSocket Service for real-time updates
 * Manages WebSocket connection to AWS API Gateway WebSocket API
 */

import config from '@/config'
import authService from './authService'

class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.messageHandlers = []
    this.connectionHandlers = []
    this.isConnecting = false
  }

  /**
   * Connect to WebSocket API
   * @param {string} fileId - Optional file ID to associate with connection
   * @returns {Promise<void>}
   */
  async connect(fileId = '') {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    if (this.isConnecting) {
      console.log('WebSocket connection in progress')
      return
    }

    this.isConnecting = true

    try {
      let token = ''
      
      try {
        const session = await authService.getUserSession()
        token = session.idToken
      } catch {
        // Use stored token from OAuth
        token = authService.getStoredToken() || ''
      }

      if (!token) {
        throw new Error('No authentication token available')
      }

      // Build WebSocket URL
      const baseUrl = config.websocketApiUrl
      if (!baseUrl) {
        throw new Error('WebSocket API URL is not configured')
      }

      // Remove trailing slash if present
      const cleanUrl = baseUrl.replace(/\/$/, '')
      const wsUrl = `${cleanUrl}?token=${encodeURIComponent(token)}${fileId ? `&file_id=${fileId}` : ''}`
      
      console.log('Connecting to WebSocket:', cleanUrl)
      console.log('Token length:', token.length)
      
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected successfully')
        this.reconnectAttempts = 0
        this.isConnecting = false
        this.notifyConnectionHandlers({ status: 'connected' })
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('WebSocket message received:', data)
          this.notifyMessageHandlers(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
          console.error('Raw message:', event.data)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        console.error('WebSocket readyState:', this.ws?.readyState)
        console.error('WebSocket URL:', wsUrl.substring(0, 100) + '...') // Log partial URL for security
        this.isConnecting = false
        this.notifyConnectionHandlers({ status: 'error', error })
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket closed')
        console.log('Close code:', event.code)
        console.log('Close reason:', event.reason || 'No reason provided')
        console.log('Was clean:', event.wasClean)
        this.isConnecting = false
        this.notifyConnectionHandlers({ status: 'closed', code: event.code, reason: event.reason })
        
        // Common close codes:
        // 1000: Normal closure
        // 1001: Going away
        // 1006: Abnormal closure (no close frame)
        // 4001-4999: Application-specific errors
        
        // Attempt to reconnect if not intentional closure
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
          setTimeout(() => this.connect(fileId), this.reconnectDelay)
        } else if (event.code === 1000) {
          console.log('WebSocket closed normally (no reconnect)')
        } else {
          console.log('Max reconnection attempts reached or connection closed intentionally')
        }
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      this.isConnecting = false
      throw error
    }
  }

  /**
   * Send message through WebSocket
   * @param {object} data
   */
  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.error('WebSocket is not connected')
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.reconnectAttempts = this.maxReconnectAttempts // Prevent reconnection
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  /**
   * Register message handler
   * @param {function} handler - Function to handle messages
   * @returns {function} Unsubscribe function
   */
  onMessage(handler) {
    this.messageHandlers.push(handler)
    return () => {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler)
    }
  }

  /**
   * Register connection status handler
   * @param {function} handler - Function to handle connection status changes
   * @returns {function} Unsubscribe function
   */
  onConnectionChange(handler) {
    this.connectionHandlers.push(handler)
    return () => {
      this.connectionHandlers = this.connectionHandlers.filter(h => h !== handler)
    }
  }

  /**
   * Notify all message handlers
   * @param {object} data
   */
  notifyMessageHandlers(data) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(data)
      } catch (error) {
        console.error('Message handler error:', error)
      }
    })
  }

  /**
   * Notify all connection handlers
   * @param {object} status
   */
  notifyConnectionHandlers(status) {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(status)
      } catch (error) {
        console.error('Connection handler error:', error)
      }
    })
  }

  /**
   * Get connection status
   * @returns {string}
   */
  getStatus() {
    if (!this.ws) return 'disconnected'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'closing'
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'unknown'
    }
  }
}

export default new WebSocketService()

