<template>
  <div class="upload-container">
    <div class="upload-card">
      <h1>上传文件</h1>
      <p class="subtitle">支持图片、视频、音频文件</p>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <div v-if="success" class="success-message">
        {{ success }}
      </div>

      <div class="upload-area" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
        <input
          ref="fileInput"
          type="file"
          accept="image/*,video/*,audio/*"
          @change="handleFileSelect"
          style="display: none"
        />
        <div v-if="!uploading" class="upload-content">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <p>点击或拖拽文件到这里</p>
          <p class="file-hint">支持 JPG, PNG, MP4, MOV, MP3, WAV 等格式</p>
        </div>
        <div v-else class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <p>上传中... {{ Math.round(uploadProgress) }}%</p>
        </div>
      </div>

      <div v-if="currentFile" class="file-info">
        <p><strong>文件：</strong>{{ currentFile.name }}</p>
        <p><strong>类型：</strong>{{ currentFile.type }}</p>
        <p><strong>大小：</strong>{{ formatFileSize(currentFile.size) }}</p>
        <p v-if="fileId"><strong>文件 ID：</strong>{{ fileId }}</p>
      </div>

      <div v-if="fileId" class="file-status">
        <h3>处理状态</h3>
        <div class="status-item">
          <span :class="{ completed: fileStatus.uploaded }">
            {{ fileStatus.uploaded ? '✓' : '○' }} 上传完成
          </span>
        </div>
        <div class="status-item">
          <span :class="{ completed: fileStatus.thumbnail }">
            {{ fileStatus.thumbnail ? '✓' : '○' }} 缩略图生成
          </span>
        </div>
        <div class="status-item">
          <span :class="{ completed: fileStatus.tagged }">
            {{ fileStatus.tagged ? '✓' : '○' }} 标签识别
          </span>
        </div>
      </div>

      <div v-if="fileData.thumbnail_url" class="thumbnail-preview">
        <h3>缩略图预览</h3>
        <img :src="fileData.thumbnail_url" alt="缩略图" />
      </div>

      <div v-if="Object.keys(fileData.tags || {}).length > 0" class="tags-display">
        <h3>识别结果</h3>
        <div class="tags-list">
          <div v-for="(count, species) in fileData.tags" :key="species" class="tag-item">
            <span class="species-name">{{ species }}</span>
            <span class="species-count">x{{ count }}</span>
          </div>
        </div>
      </div>

      <div class="actions">
        <button @click="resetUpload" class="reset-button">重新上传</button>
        <button v-if="fileId" @click="goToFiles" class="view-button">查看所有文件</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { requestUploadFile, uploadToS3 } from '@/utils/api'
import { getToken } from '@/utils/auth'
import websocketService from '@/services/websocket'

const router = useRouter()
const fileInput = ref(null)
const currentFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const fileId = ref(null)
const error = ref('')
const success = ref('')

const fileStatus = ref({
  uploaded: false,
  thumbnail: false,
  tagged: false
})

const fileData = ref({
  thumbnail_url: null,
  tags: {}
})

const triggerFileInput = () => {
  if (!uploading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    startUpload(file)
  }
}

const handleDrop = (event) => {
  event.preventDefault()
  const file = event.dataTransfer.files[0]
  if (file && !uploading.value) {
    startUpload(file)
  }
}

const startUpload = async (file) => {
  if (!getToken()) {
    error.value = '请先登录'
    router.push('/login')
    return
  }

  currentFile.value = file
  uploading.value = true
  uploadProgress.value = 0
  error.value = ''
  success.value = ''
  fileId.value = null
  fileStatus.value = { uploaded: false, thumbnail: false, tagged: false }
  fileData.value = { thumbnail_url: null, tags: {} }

  try {
    // 1. 请求 presigned URL
    const uploadInfo = await requestUploadFile(file.name, file.type)
    fileId.value = uploadInfo.file_id

    // 2. 上传文件到 S3
    await uploadToS3(uploadInfo.presign_url, file, (progress) => {
      uploadProgress.value = progress
    })

    fileStatus.value.uploaded = true
    success.value = '文件上传成功，正在处理...'

    // 3. 建立 WebSocket 连接接收更新
    connectWebSocket(uploadInfo.file_id)
  } catch (err) {
    error.value = err.message || '上传失败'
    uploading.value = false
  }
}

const connectWebSocket = (id) => {
  websocketService.connect(
    id,
    (message) => {
      handleWebSocketMessage(message)
    },
    (err) => {
      console.error('WebSocket error:', err)
      error.value = 'WebSocket 连接错误，但文件已上传成功'
    },
    () => {
      console.log('WebSocket closed')
    }
  )
}

const handleWebSocketMessage = (message) => {
  if (message.type === 'FILE_UPDATE') {
    if (message.thumbnail_url) {
      fileData.value.thumbnail_url = message.thumbnail_url
      fileStatus.value.thumbnail = true
    }
    if (message.tags && Object.keys(message.tags).length > 0) {
      // 转换 DynamoDB Map 格式到普通对象
      const tags = {}
      for (const [key, value] of Object.entries(message.tags)) {
        if (value.N) {
          tags[key] = parseInt(value.N)
        } else if (typeof value === 'number') {
          tags[key] = value
        }
      }
      fileData.value.tags = tags
      fileStatus.value.tagged = true
    }
  }
}

const resetUpload = () => {
  currentFile.value = null
  uploading.value = false
  uploadProgress.value = 0
  fileId.value = null
  error.value = ''
  success.value = ''
  fileStatus.value = { uploaded: false, thumbnail: false, tagged: false }
  fileData.value = { thumbnail_url: null, tags: {} }
  websocketService.disconnect()
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const goToFiles = () => {
  router.push('/files')
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

onUnmounted(() => {
  websocketService.disconnect()
})
</script>

<style scoped>
.upload-container {
  min-height: 100vh;
  padding: 40px 20px;
  background: #f5f7fa;
}

.upload-card {
  max-width: 800px;
  margin: 0 auto;
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
  margin: 0 0 10px 0;
  color: #333;
  text-align: center;
}

.subtitle {
  text-align: center;
  color: #666;
  margin-bottom: 30px;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.success-message {
  background: #efe;
  color: #3c3;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 60px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 30px;
}

.upload-area:hover {
  border-color: #667eea;
  background: #f8f9ff;
}

.upload-content svg {
  color: #667eea;
  margin-bottom: 20px;
}

.upload-content p {
  margin: 10px 0;
  color: #666;
}

.file-hint {
  font-size: 14px;
  color: #999;
}

.upload-progress {
  padding: 20px;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s;
}

.file-info {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.file-info p {
  margin: 8px 0;
  color: #333;
}

.file-status {
  margin-bottom: 20px;
}

.file-status h3 {
  margin-bottom: 15px;
  color: #333;
}

.status-item {
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.status-item span {
  color: #999;
}

.status-item span.completed {
  color: #3c3;
  font-weight: 500;
}

.thumbnail-preview {
  margin-bottom: 20px;
}

.thumbnail-preview h3 {
  margin-bottom: 15px;
  color: #333;
}

.thumbnail-preview img {
  max-width: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tags-display {
  margin-bottom: 20px;
}

.tags-display h3 {
  margin-bottom: 15px;
  color: #333;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag-item {
  background: #667eea;
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.species-name {
  font-weight: 500;
}

.species-count {
  background: rgba(255, 255, 255, 0.3);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 30px;
}

.reset-button,
.view-button {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.reset-button {
  background: #f0f0f0;
  color: #333;
}

.reset-button:hover {
  background: #e0e0e0;
}

.view-button {
  background: #667eea;
  color: white;
}

.view-button:hover {
  background: #5568d3;
}
</style>

