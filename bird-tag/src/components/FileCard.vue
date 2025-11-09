<template>
  <div class="file-card">
    <!-- Thumbnail or Icon -->
    <div class="file-thumbnail">
      <img
        v-if="file.thumbnail_url"
        :src="file.thumbnail_url"
        :alt="file.file_id"
        class="thumbnail-image"
        @error="handleImageError"
      />
      <div v-else class="thumbnail-placeholder">
        <span class="file-type-icon">{{ fileTypeIcon }}</span>
      </div>
      
      <!-- Processing Indicator -->
      <div v-if="isProcessing" class="processing-badge">
        <span class="processing-spinner"></span>
        Processing...
      </div>
    </div>

    <!-- File Info -->
    <div class="file-info">
      <div class="file-header">
        <span class="file-type-badge" :class="'badge-' + file.file_type">
          {{ file.file_type || 'unknown' }}
        </span>
        <span class="file-date">{{ formatDate(file.upload_timestamp) }}</span>
      </div>

      <p class="file-id">ID: {{ shortId }}</p>

      <!-- Tags Section -->
      <div class="tags-section">
        <h4 class="tags-title">Detected Tags:</h4>
        <div v-if="hasTags" class="tags-list">
          <div
            v-for="(count, species) in file.tags"
            :key="species"
            class="tag-item"
          >
            <span class="tag-name">{{ species }}</span>
            <span class="tag-count">{{ count }}</span>
          </div>
        </div>
        <p v-else class="no-tags">
          {{ isProcessing ? 'Analyzing...' : 'No tags detected' }}
        </p>
      </div>

      <!-- Actions -->
      <div class="file-actions">
        <button
          v-if="file.s3_url"
          @click="viewOriginal"
          class="btn btn-link"
          title="View original file"
        >
          <span>🔗</span> View Original
        </button>
        <button
          @click="copyId"
          class="btn btn-link"
          title="Copy file ID"
        >
          <span>📋</span> Copy ID
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  file: {
    type: Object,
    required: true,
  },
})

const imageError = ref(false)

const shortId = computed(() => {
  return props.file.file_id?.substring(0, 12) + '...' || 'N/A'
})

const fileTypeIcon = computed(() => {
  switch (props.file.file_type) {
    case 'image':
      return '🖼️'
    case 'video':
      return '🎬'
    case 'audio':
      return '🎵'
    default:
      return '📄'
  }
})

const hasTags = computed(() => {
  return props.file.tags && Object.keys(props.file.tags).length > 0
})

const isProcessing = computed(() => {
  // File is processing if thumbnail exists but no tags yet
  // or if neither thumbnail nor tags exist
  return !hasTags.value && (!props.file.thumbnail_url || !props.file.s3_url)
})

const formatDate = (timestamp) => {
  if (!timestamp) return 'Unknown date'
  
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return 'Invalid date'
  }
}

const handleImageError = () => {
  imageError.value = true
}

const viewOriginal = () => {
  if (props.file.s3_url) {
    window.open(props.file.s3_url, '_blank')
  }
}

const copyId = async () => {
  try {
    await navigator.clipboard.writeText(props.file.file_id)
    alert('File ID copied to clipboard!')
  } catch (error) {
    console.error('Failed to copy:', error)
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = props.file.file_id
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      alert('File ID copied to clipboard!')
    } catch (err) {
      console.error('Fallback copy failed:', err)
    }
    document.body.removeChild(textArea)
  }
}
</script>

<style scoped>
.file-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s, box-shadow 0.3s;
}

.file-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
}

.file-thumbnail {
  position: relative;
  width: 100%;
  height: 200px;
  background: #f5f5f5;
  overflow: hidden;
}

.thumbnail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea33 0%, #764ba233 100%);
}

.file-type-icon {
  font-size: 4rem;
}

.processing-badge {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background: rgba(255, 255, 255, 0.95);
  color: #667eea;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.processing-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.file-info {
  padding: 16px;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.file-type-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
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

.file-date {
  font-size: 0.8rem;
  color: #999;
}

.file-id {
  font-size: 0.85rem;
  color: #666;
  margin: 0 0 16px 0;
  font-family: 'Courier New', monospace;
}

.tags-section {
  margin-bottom: 16px;
}

.tags-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  margin: 0 0 8px 0;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 0.85rem;
}

.tag-name {
  font-weight: 500;
}

.tag-count {
  background: rgba(255, 255, 255, 0.3);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 600;
}

.no-tags {
  font-size: 0.85rem;
  color: #999;
  font-style: italic;
  margin: 0;
}

.file-actions {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.btn {
  border: none;
  background: none;
  cursor: pointer;
  transition: all 0.3s;
  padding: 0;
}

.btn-link {
  color: #667eea;
  font-size: 0.85rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-link:hover {
  color: #764ba2;
  text-decoration: underline;
}
</style>

