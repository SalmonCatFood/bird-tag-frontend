<template>
  <div class="card-details-container">
    <!-- Header -->
    <header class="details-header">
      <div class="header-content">
        <button @click="goBack" class="btn-back">
          <span>←</span> Back
        </button>
        <h1 class="page-title">File Details</h1>
        <div class="header-actions">
          <span class="user-info">{{ userEmail }}</span>
          <button @click="handleSignOut" class="btn btn-secondary">
            Sign Out
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="details-main" v-if="!loading && !error">
      <div class="content-wrapper">
        <!-- File Preview Section -->
        <section class="preview-section">
          <div class="preview-container">
            <!-- Toggle Switch for Original/Annotated (only for video) -->
            <div v-if="(fileData.file_type === 'video' || fileData.file_type === 'Video') && hasAnnotatedFile" class="toggle-container">
              <label class="toggle-label">
                <span class="toggle-text">Show Annotated Video</span>
                <div class="toggle-wrapper">
                  <input
                    type="checkbox"
                    v-model="showAnnotated"
                    class="toggle-switch"
                    id="annotated-toggle"
                  />
                  <label for="annotated-toggle" class="toggle-slider"></label>
                </div>
              </label>
            </div>

            <!-- Image Preview -->
            <div v-if="fileData.file_type === 'image' || fileData.file_type === 'Image'" class="media-preview">
              <img
                v-if="currentMediaUrl"
                :src="currentMediaUrl"
                :alt="fileData.file_id"
                class="preview-image"
                @error="handleImageError"
              />
              <div v-else-if="fileData.thumbnail_url" class="thumbnail-fallback">
                <img
                  :src="fileData.thumbnail_url"
                  :alt="fileData.file_id"
                  class="preview-thumbnail"
                />
                <p class="fallback-text">Original file not available, showing thumbnail</p>
              </div>
              <div v-else class="no-preview">
                <span class="no-preview-icon">🖼️</span>
                <p>Image preview not available</p>
              </div>
            </div>

            <!-- Video Preview -->
            <div v-else-if="fileData.file_type === 'video' || fileData.file_type === 'Video'" class="media-preview">
              <video
                v-if="currentMediaUrl"
                :src="currentMediaUrl"
                controls
                class="preview-video"
                @error="handleVideoError"
                :key="currentMediaUrl"
              >
                Your browser does not support the video tag.
              </video>
              <div v-else-if="fileData.thumbnail_url" class="thumbnail-fallback">
                <img
                  :src="fileData.thumbnail_url"
                  :alt="fileData.file_id"
                  class="preview-thumbnail"
                />
                <p class="fallback-text">Video file not available, showing thumbnail</p>
              </div>
              <div v-else class="no-preview">
                <span class="no-preview-icon">🎬</span>
                <p>Video preview not available</p>
              </div>
            </div>

            <!-- Audio Preview -->
            <div v-else-if="fileData.file_type === 'audio' || fileData.file_type === 'Audio'" class="media-preview">
              <div v-if="currentMediaUrl" class="audio-player-container">
                <div class="audio-icon">🎵</div>
                <audio
                  :src="currentMediaUrl"
                  controls
                  class="preview-audio"
                  @error="handleAudioError"
                  :key="currentMediaUrl"
                >
                  Your browser does not support the audio tag.
                </audio>
              </div>
              <div v-else-if="fileData.thumbnail_url" class="thumbnail-fallback">
                <img
                  :src="fileData.thumbnail_url"
                  :alt="fileData.file_id"
                  class="preview-thumbnail"
                />
                <p class="fallback-text">Audio file not available, showing thumbnail</p>
              </div>
              <div v-else class="no-preview">
                <span class="no-preview-icon">🎵</span>
                <p>Audio preview not available</p>
              </div>
            </div>

            <!-- Unknown Type -->
            <div v-else class="media-preview">
              <div class="no-preview">
                <span class="no-preview-icon">📄</span>
                <p>Preview not available for this file type</p>
              </div>
            </div>
          </div>
        </section>

        <!-- File Information Section -->
        <section class="info-section">
          <h2>File Information</h2>
          
          <div class="info-grid">
            <div class="info-item">
              <label>File ID</label>
              <div class="info-value">
                <code>{{ fileData.file_id }}</code>
                <button @click="copyFileId" class="btn-copy" title="Copy File ID">
                  📋
                </button>
              </div>
            </div>

            <div class="info-item">
              <label>File Type</label>
              <div class="info-value">
                <span class="file-type-badge" :class="'badge-' + (fileData.file_type || 'unknown').toLowerCase()">
                  {{ fileData.file_type || 'Unknown' }}
                </span>
              </div>
            </div>

            <div class="info-item">
              <label>Upload Date</label>
              <div class="info-value">
                {{ formatDate(fileData.upload_timestamp) }}
              </div>
            </div>

            <div class="info-item" v-if="fileData.status">
              <label>Status</label>
              <div class="info-value">
                <span class="status-badge" :class="'status-' + (fileData.status || 'pending').toLowerCase()">
                  {{ fileData.status }}
                </span>
              </div>
            </div>
          </div>

          <!-- Tags Section -->
          <div class="tags-section">
            <h3>Detected Tags</h3>
            <div v-if="hasTags" class="tags-list">
              <div
                v-for="(count, species) in fileData.tags"
                :key="species"
                class="tag-item"
              >
                <span class="tag-name">{{ species }}</span>
                <span class="tag-count">{{ count }}</span>
              </div>
            </div>
            <p v-else class="no-tags">
              {{ isProcessing ? 'Analyzing...' : 'No tags detected yet' }}
            </p>
          </div>

          <!-- Tags Timestamp Section -->
          <div v-if="hasTagsTimestamp" class="metadata-section">
            <h3>Tags Timestamp</h3>
            <pre class="metadata-json">{{ formatMetadata(fileData.tags_timestemp) }}</pre>
          </div>

          <!-- Additional Metadata Section -->
          <div v-if="hasAdditionalMetadata" class="metadata-section">
            <h3>Additional Metadata</h3>
            <pre class="metadata-json">{{ formatMetadata(fileData.additional_metadata) }}</pre>
          </div>

          <!-- Actions -->
          <div class="actions-section">
            <button
              v-if="fileData.s3_url"
              @click="openOriginal"
              class="btn btn-primary"
            >
              <span>🔗</span> Open Original File
            </button>
            <button
              v-if="fileData.annotated_output_url"
              @click="openAnnotated"
              class="btn btn-primary"
            >
              <span>🎬</span> Open Annotated File
            </button>
            <button
              v-if="fileData.thumbnail_url"
              @click="openThumbnail"
              class="btn btn-secondary"
            >
              <span>🖼️</span> View Thumbnail
            </button>
          </div>
        </section>
      </div>
    </main>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>Loading file details...</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-container">
      <div class="error-icon">⚠️</div>
      <h2>Error Loading File Details</h2>
      <p>{{ error }}</p>
      <button @click="loadFileDetails" class="btn btn-primary">Retry</button>
      <button @click="goBack" class="btn btn-secondary">Go Back</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import authService from '@/services/authService'
import apiService from '@/services/apiService'
import websocketService from '@/services/websocketService'

const router = useRouter()
const route = useRoute()

const userEmail = ref('')
const fileData = ref({})
const loading = ref(true)
const error = ref('')
const fileId = ref('')
const showAnnotated = ref(false)

const hasTags = computed(() => {
  return fileData.value.tags && Object.keys(fileData.value.tags).length > 0
})

const hasAdditionalMetadata = computed(() => {
  return fileData.value.additional_metadata && 
         Object.keys(fileData.value.additional_metadata).length > 0
})

const hasTagsTimestamp = computed(() => {
  return fileData.value.tags_timestemp && 
         (Array.isArray(fileData.value.tags_timestemp) ? fileData.value.tags_timestemp.length > 0 : 
          Object.keys(fileData.value.tags_timestemp).length > 0)
})

const hasAnnotatedFile = computed(() => {
  return !!fileData.value.annotated_output_url
})

const currentMediaUrl = computed(() => {
  // For video files, use annotated if toggle is on, otherwise use original
  if ((fileData.value.file_type === 'video' || fileData.value.file_type === 'Video') && hasAnnotatedFile.value) {
    return showAnnotated.value ? fileData.value.annotated_output_url : fileData.value.s3_url
  }
  // For other file types, always use original
  return fileData.value.s3_url
})

const isProcessing = computed(() => {
  return !hasTags.value && (!fileData.value.thumbnail_url || !fileData.value.s3_url)
})

const loadFileDetails = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const details = await apiService.getCardDetails(fileId.value)
    fileData.value = details
    console.log('File details loaded:', details)
  } catch (err) {
    console.error('Failed to load file details:', err)
    if (err.response?.status === 404) {
      error.value = 'File not found'
    } else if (err.response?.status === 403) {
      error.value = 'You do not have access to this file'
    } else if (err.response?.status === 401) {
      error.value = 'Authentication failed. Please sign in again.'
      router.push('/login')
    } else {
      error.value = err.response?.data?.error || err.message || 'Failed to load file details'
    }
  } finally {
    loading.value = false
  }
}

const formatDate = (timestamp) => {
  if (!timestamp) return 'Unknown date'
  
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    })
  } catch {
    return timestamp
  }
}

const formatMetadata = (metadata) => {
  if (!metadata || typeof metadata !== 'object') return '{}'
  return JSON.stringify(metadata, null, 2)
}

const copyFileId = async () => {
  try {
    await navigator.clipboard.writeText(fileData.value.file_id)
    alert('File ID copied to clipboard!')
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

const openOriginal = () => {
  if (fileData.value.s3_url) {
    window.open(fileData.value.s3_url, '_blank')
  }
}

const openThumbnail = () => {
  if (fileData.value.thumbnail_url) {
    window.open(fileData.value.thumbnail_url, '_blank')
  }
}

const openAnnotated = () => {
  if (fileData.value.annotated_output_url) {
    const url = fileData.value.annotated_output_url
    console.log('Opening annotated file URL:', url)
    
    // 尝试打开 URL
    const newWindow = window.open(url, '_blank')
    
    // 检查是否成功打开（可能被弹窗阻止）
    if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
      console.error('Failed to open annotated file. URL:', url)
      alert('Failed to open annotated file. Please check the browser console for details.')
    } else {
      // 监听新窗口的错误（如果可能）
      newWindow.addEventListener('error', (e) => {
        console.error('Error loading annotated file:', e)
      })
    }
  } else {
    console.warn('No annotated_output_url available')
  }
}

const handleImageError = () => {
  console.error('Failed to load image')
}

const handleVideoError = () => {
  console.error('Failed to load video')
}

const handleAudioError = () => {
  console.error('Failed to load audio')
}

const goBack = () => {
  router.push('/dashboard')
}

const handleSignOut = () => {
  websocketService.disconnect()
  authService.globalSignOut()
}

onMounted(async () => {
  try {
    // Get user info
    const session = await authService.getUserSession()
    userEmail.value = session.user.email || 'User'
    
    // Get file ID from route
    fileId.value = route.params.fileId
    if (!fileId.value) {
      error.value = 'File ID is required'
      loading.value = false
      return
    }
    
    // Load file details
    await loadFileDetails()
  } catch (err) {
    console.error('Card details initialization error:', err)
    if (err.message?.includes('No user found') || err.message?.includes('Session')) {
      router.push('/login')
    } else {
      error.value = err.message || 'Failed to initialize'
      loading.value = false
    }
  }
})
</script>

<style scoped>
.card-details-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.details-header {
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
  gap: 20px;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-back:hover {
  background: #667eea;
  color: white;
}

.page-title {
  flex: 1;
  font-size: 1.8rem;
  margin: 0;
  color: #333;
  font-weight: 700;
  text-align: center;
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

.details-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 30px;
}

.content-wrapper {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
}

section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.preview-section {
  position: sticky;
  top: 100px;
  height: fit-content;
}

.preview-container {
  width: 100%;
}

.media-preview {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: #f5f5f5;
}

.preview-image,
.preview-video {
  width: 100%;
  height: auto;
  display: block;
}

.preview-audio {
  width: 100%;
  margin-top: 20px;
}

.audio-player-container {
  padding: 40px;
  text-align: center;
}

.audio-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.thumbnail-fallback {
  position: relative;
  width: 100%;
  padding-top: 56.25%; /* 16:9 aspect ratio */
  background: #f5f5f5;
}

.preview-thumbnail {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.fallback-text {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 12px;
  margin: 0;
  text-align: center;
  font-size: 0.9rem;
}

.no-preview {
  padding: 80px 40px;
  text-align: center;
  color: #999;
}

.no-preview-icon {
  font-size: 4rem;
  display: block;
  margin-bottom: 20px;
}

.info-section h2 {
  margin: 0 0 24px 0;
  font-size: 1.6rem;
  color: #333;
}

.info-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 30px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-value code {
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  color: #333;
  flex: 1;
  word-break: break-all;
}

.btn-copy {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-copy:hover {
  background: #f0f0f0;
}

.file-type-badge,
.status-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 16px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-image {
  background: #e3f2fd;
  color: #1976d2;
}

.badge-video {
  background: #f3e5f5;
  color: #7b1fa2;
}

.badge-audio {
  background: #fff3e0;
  color: #e65100;
}

.badge-unknown {
  background: #f5f5f5;
  color: #757575;
}

.status-pending {
  background: #fff3e0;
  color: #e65100;
}

.status-completed {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-processing {
  background: #e3f2fd;
  color: #1976d2;
}

.tags-section {
  margin-bottom: 30px;
}

.tags-section h3 {
  margin: 0 0 16px 0;
  font-size: 1.2rem;
  color: #333;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tag-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 0.9rem;
}

.tag-name {
  font-weight: 500;
}

.tag-count {
  background: rgba(255, 255, 255, 0.3);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.no-tags {
  color: #999;
  font-style: italic;
  margin: 0;
}

.metadata-section {
  margin-bottom: 30px;
}

.metadata-section h3 {
  margin: 0 0 16px 0;
  font-size: 1.2rem;
  color: #333;
}

.metadata-json {
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.6;
  color: #333;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
}

.toggle-container {
  margin-bottom: 20px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.toggle-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  user-select: none;
}

.toggle-text {
  font-size: 0.95rem;
  font-weight: 500;
  color: #333;
}

.toggle-wrapper {
  position: relative;
  display: inline-block;
}

.toggle-switch {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
  background: #ccc;
  border-radius: 13px;
  cursor: pointer;
  transition: background 0.3s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  transition: transform 0.3s;
}

.toggle-switch:checked + .toggle-slider {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.toggle-switch:checked + .toggle-slider::before {
  transform: translateX(24px);
}

.actions-section {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn {
  padding: 12px 24px;
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

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
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

.loading-container,
.error-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 80px 30px;
  text-align: center;
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

.error-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.error-container h2 {
  margin: 0 0 16px 0;
  color: #c62828;
}

.error-container p {
  margin: 0 0 24px 0;
  color: #666;
}

.error-container .btn {
  margin: 0 8px;
}

@media (max-width: 1024px) {
  .content-wrapper {
    grid-template-columns: 1fr;
  }

  .preview-section {
    position: static;
  }
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
  }

  .page-title {
    font-size: 1.4rem;
  }

  .actions-section {
    flex-direction: column;
  }

  .actions-section .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>

