<template>
  <div class="dashboard-container">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-content">
        <h1 class="app-title">🐦 Bird Tag</h1>
        <div class="header-actions">
          <span class="user-info">{{ userEmail }}</span>
          <button @click="handleSignOut" class="btn btn-secondary">
            Sign Out
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="dashboard-main">
      <div class="content-wrapper">
        <!-- Upload Section -->
        <section class="upload-section">
          <h2>Upload Files</h2>
          <p class="section-description">
            Upload images, videos, or audio files for automatic tagging and analysis
          </p>

          <div
            class="upload-dropzone"
            :class="{ 'drag-over': isDragOver }"
            @drop.prevent="handleDrop"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
          >
            <div class="dropzone-content">
              <div class="upload-icon">📁</div>
              <p class="dropzone-text">
                Drag and drop files here or
                <label class="file-label">
                  browse
                  <input
                    type="file"
                    ref="fileInput"
                    @change="handleFileSelect"
                    multiple
                    accept="image/*,video/*,audio/*"
                    style="display: none"
                  />
                </label>
              </p>
              <p class="dropzone-hint">
                Supported formats: Images (JPG, PNG), Videos (MP4, MOV), Audio (MP3, WAV)
              </p>
            </div>
          </div>

          <!-- Upload Queue -->
          <div v-if="uploadQueue.length > 0" class="upload-queue">
            <h3>Uploading Files</h3>
            <div
              v-for="item in uploadQueue"
              :key="item.id"
              class="upload-item"
            >
              <div class="upload-item-info">
                <span class="file-icon">{{ getFileIcon(item.file.type) }}</span>
                <div class="upload-item-details">
                  <p class="file-name">{{ item.file.name }}</p>
                  <p class="file-size">{{ formatFileSize(item.file.size) }}</p>
                </div>
              </div>
              <div class="upload-progress">
                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    :style="{ width: item.progress + '%' }"
                  ></div>
                </div>
                <span class="progress-text">{{ item.progress }}%</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Files List Section -->
        <section class="files-section">
          <div class="section-header">
            <h2>Your Files</h2>
            <button @click="loadFiles" class="btn btn-secondary btn-sm">
              <span>🔄</span> Refresh
            </button>
          </div>

          <!-- WebSocket Status -->
          <div class="ws-status" :class="'ws-' + wsStatus">
            <span class="status-dot"></span>
            {{ wsStatusText }}
          </div>

          <!-- API Error Message -->
          <div v-if="apiError" class="api-error">
            <div class="error-icon">⚠️</div>
            <div class="error-content">
              <p class="error-title">API Connection Error</p>
              <p class="error-message">{{ apiError }}</p>
              <p class="error-hint">
                Please check the API Gateway configuration. See 
                <code>note/API-Gateway-Configuration.md</code> for setup instructions.
              </p>
            </div>
            <button @click="apiError = ''" class="error-close">×</button>
          </div>

          <!-- Loading State -->
          <div v-if="loading" class="loading-container">
            <div class="spinner"></div>
            <p>Loading files...</p>
          </div>

          <!-- Empty State -->
          <div v-else-if="files.length === 0" class="empty-state">
            <div class="empty-icon">📋</div>
            <p>No files yet. Upload your first file to get started!</p>
          </div>

          <!-- Files Grid -->
          <div v-else class="files-grid">
            <FileCard
              v-for="file in files"
              :key="file.file_id"
              :file="file"
            />
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import authService from '@/services/authService'
import apiService from '@/services/apiService'
import websocketService from '@/services/websocketService'
import FileCard from '@/components/FileCard.vue'

const router = useRouter()

const userEmail = ref('')
const files = ref([])
const loading = ref(false)
const uploadQueue = ref([])
const isDragOver = ref(false)
const wsStatus = ref('disconnected')
const fileInput = ref(null)
const apiError = ref('')

let unsubscribeWsMessage = null
let unsubscribeWsConnection = null

const wsStatusText = computed(() => {
  switch (wsStatus.value) {
    case 'connected':
      return 'Connected - Real-time updates active'
    case 'connecting':
      return 'Connecting...'
    case 'disconnected':
      return 'Disconnected - Updates paused'
    default:
      return 'Unknown'
  }
})

const handleSignOut = () => {
  websocketService.disconnect()
  authService.globalSignOut()
}

const loadFiles = async () => {
  loading.value = true
  apiError.value = ''
  try {
    const filesList = await apiService.listFiles()
    files.value = filesList
  } catch (error) {
    console.error('Failed to load files:', error)
    if (error.response?.status === 0 || error.code === 'ERR_NETWORK') {
      apiError.value = 'Unable to connect to API. Please check your API Gateway configuration (CORS settings).'
    } else if (error.response?.status === 401) {
      apiError.value = 'Authentication failed. Please sign in again.'
      router.push('/login')
    } else {
      apiError.value = error.response?.data?.message || error.message || 'Failed to load files. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  selectedFiles.forEach(file => uploadFile(file))
  // Reset input
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleDrop = (event) => {
  isDragOver.value = false
  const droppedFiles = Array.from(event.dataTransfer.files)
  droppedFiles.forEach(file => uploadFile(file))
}

const uploadFile = async (file) => {
  const uploadId = Date.now() + Math.random()
  const uploadItem = {
    id: uploadId,
    file: file,
    progress: 0,
    status: 'uploading',
  }

  uploadQueue.value.push(uploadItem)

  try {
    // Request upload URL
    const { file_id, presign_url, s3_key } = await apiService.requestUpload(
      file.name,
      file.type
    )

    console.log(`Upload requested: file_id=${file_id}, key=${s3_key}`)

    // Upload to S3
    await apiService.uploadToS3(presign_url, file, (progress) => {
      const item = uploadQueue.value.find(i => i.id === uploadId)
      if (item) {
        item.progress = progress
      }
    })

    // Remove from queue after short delay
    setTimeout(() => {
      uploadQueue.value = uploadQueue.value.filter(i => i.id !== uploadId)
    }, 2000)

    // File will appear in list via WebSocket update
    console.log(`Upload completed: file_id=${file_id}`)
  } catch (error) {
    console.error('Upload failed:', error)
    const item = uploadQueue.value.find(i => i.id === uploadId)
    if (item) {
      item.status = 'error'
      item.progress = 0
    }
  }
}

const getFileIcon = (mimeType) => {
  if (mimeType.startsWith('image/')) return '🖼️'
  if (mimeType.startsWith('video/')) return '🎬'
  if (mimeType.startsWith('audio/')) return '🎵'
  return '📄'
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const handleWebSocketMessage = (data) => {
  console.log('WebSocket message:', data)
  
  if (data.type === 'FILE_UPDATE') {
    // Update or add file to list
    const existingIndex = files.value.findIndex(f => f.file_id === data.file_id)
    
    if (existingIndex >= 0) {
      // Update existing file
      files.value[existingIndex] = {
        ...files.value[existingIndex],
        ...data,
      }
    } else {
      // Add new file
      files.value.unshift(data)
    }
  }
}

const handleWebSocketConnection = (status) => {
  console.log('WebSocket status:', status)
  wsStatus.value = status.status
}

onMounted(async () => {
  try {
    // Get user info
    const session = await authService.getUserSession()
    userEmail.value = session.user.email || 'User'
    
    // Load files
    await loadFiles()
    
    // Connect WebSocket
    await websocketService.connect()
    wsStatus.value = websocketService.getStatus()
    
    // Subscribe to WebSocket events
    unsubscribeWsMessage = websocketService.onMessage(handleWebSocketMessage)
    unsubscribeWsConnection = websocketService.onConnectionChange(handleWebSocketConnection)
  } catch (error) {
    console.error('Dashboard initialization error:', error)
    if (error.message?.includes('No user found') || error.message?.includes('Session')) {
      router.push('/login')
    }
  }
})

onUnmounted(() => {
  // Clean up WebSocket subscriptions
  if (unsubscribeWsMessage) unsubscribeWsMessage()
  if (unsubscribeWsConnection) unsubscribeWsConnection()
  websocketService.disconnect()
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.dashboard-header {
  background: white;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-title {
  font-size: 1.8rem;
  margin: 0;
  color: #333;
  font-weight: 700;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info {
  color: #666;
  font-size: 0.95rem;
}

.dashboard-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 30px;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

h2 {
  margin: 0 0 10px 0;
  font-size: 1.6rem;
  color: #333;
}

.section-description {
  margin: 0 0 24px 0;
  color: #666;
  font-size: 0.95rem;
}

.upload-dropzone {
  border: 3px dashed #d0d0d0;
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  transition: all 0.3s;
  cursor: pointer;
  background: #fafafa;
}

.upload-dropzone:hover,
.upload-dropzone.drag-over {
  border-color: #667eea;
  background: #f0f3ff;
}

.dropzone-content {
  pointer-events: none;
}

.upload-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.dropzone-text {
  font-size: 1.1rem;
  color: #555;
  margin: 0 0 10px 0;
}

.file-label {
  color: #667eea;
  font-weight: 600;
  cursor: pointer;
  pointer-events: all;
}

.file-label:hover {
  text-decoration: underline;
}

.dropzone-hint {
  font-size: 0.85rem;
  color: #999;
  margin: 0;
}

.upload-queue {
  margin-top: 30px;
}

.upload-queue h3 {
  font-size: 1.2rem;
  margin: 0 0 16px 0;
  color: #333;
}

.upload-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.upload-item-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.file-icon {
  font-size: 2rem;
}

.upload-item-details {
  flex: 1;
}

.file-name {
  margin: 0 0 4px 0;
  font-weight: 500;
  color: #333;
}

.file-size {
  margin: 0;
  font-size: 0.85rem;
  color: #666;
}

.upload-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s;
}

.progress-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: #667eea;
  min-width: 40px;
  text-align: right;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.ws-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  margin-bottom: 20px;
}

.api-error {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  margin-bottom: 20px;
  position: relative;
}

.error-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.error-content {
  flex: 1;
}

.error-title {
  margin: 0 0 8px 0;
  font-weight: 600;
  color: #856404;
  font-size: 1rem;
}

.error-message {
  margin: 0 0 8px 0;
  color: #856404;
  font-size: 0.9rem;
}

.error-hint {
  margin: 0;
  color: #856404;
  font-size: 0.85rem;
  font-style: italic;
}

.error-hint code {
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
}

.error-close {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #856404;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.error-close:hover {
  background: rgba(0, 0, 0, 0.1);
}

.ws-connected {
  background: #e8f5e9;
  color: #2e7d32;
}

.ws-connecting {
  background: #fff3e0;
  color: #e65100;
}

.ws-disconnected {
  background: #ffebee;
  color: #c62828;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.loading-container {
  text-align: center;
  padding: 60px 20px;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-state p {
  color: #999;
  font-size: 1rem;
}

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-secondary {
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
}

.btn-secondary:hover {
  background: #667eea;
  color: white;
}

.btn-sm {
  padding: 8px 16px;
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .files-grid {
    grid-template-columns: 1fr;
  }
}
</style>

