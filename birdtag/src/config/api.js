// API Gateway 配置
// TODO: 部署后请更新以下 URL 为实际的 API Gateway 端点

// REST API Gateway 基础 URL
export const REST_API_BASE_URL = import.meta.env.VITE_REST_API_URL || 'https://3nlelwkvx7.execute-api.ap-southeast-2.amazonaws.com/dev'

// WebSocket API Gateway 连接 URL
export const WEBSOCKET_API_URL = import.meta.env.VITE_WEBSOCKET_API_URL || 'wss://2n94zibbvf.execute-api.ap-southeast-2.amazonaws.com/dev/'

// API 端点
export const API_ENDPOINTS = {
  UPLOAD_FILE: '/upload-file',
  GET_METADATA: (fileId) => `/metadata/${fileId}`
}

// WebSocket 路由键
export const WEBSOCKET_ROUTES = {
  CONNECT: '$connect',
  DISCONNECT: '$disconnect',
  DEFAULT: '$default'
}

