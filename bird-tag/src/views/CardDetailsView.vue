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
      <!-- Unified Media Preview Section -->
      <section class="preview-section">
        <!-- Header with Toggle -->
        <div class="preview-header">
          <div class="header-left">
            <h2>{{ showAnnotated ? '🏷️ Annotated File' : '📁 Original File' }}</h2>
            <span v-if="showAnnotated && hasAnnotatedFile" class="ai-badge">AI Processed</span>
          </div>
          <div class="header-right">
            <!-- Toggle Switch (only show if annotated file exists) -->
            <div v-if="hasAnnotatedFile" class="toggle-container">
              <span class="toggle-label-text">Original</span>
              <label class="toggle-switch-wrapper">
                <input
                  type="checkbox"
                  v-model="showAnnotated"
                  class="toggle-input"
                />
                <span class="toggle-slider"></span>
              </label>
              <span class="toggle-label-text active">Annotated</span>
            </div>
            <!-- Open in new tab button -->
            <button
              v-if="currentMediaUrl"
              @click="openCurrentInNewTab"
              class="btn-open-new-tab"
              title="Open in new tab"
            >
              ↗
            </button>
          </div>
        </div>

        <!-- Media Preview Container -->
        <div class="preview-container">
          <!-- Loading State - No files available yet -->
          <div v-if="!hasAnyFile" class="media-preview">
            <div class="loading-preview">
              <div class="loading-spinner"></div>
              <p>Processing file...</p>
              <span class="loading-hint">Your file is being analyzed</span>
            </div>
          </div>

          <!-- Image Preview -->
          <div v-else-if="isImage" class="media-preview">
            <img
              v-if="currentMediaUrl"
              :src="currentMediaUrl"
              :alt="fileData.file_id"
              class="preview-image"
              :key="currentMediaUrl"
              @error="handleMediaError"
              @load="handleMediaLoad"
            />
            <div v-else-if="fileData.thumbnail_url" class="thumbnail-fallback">
              <img
                :src="fileData.thumbnail_url"
                :alt="fileData.file_id"
                class="preview-thumbnail"
              />
              <p class="fallback-text">Full resolution not available, showing thumbnail</p>
            </div>
            <div v-else class="no-preview">
              <span class="no-preview-icon">🖼️</span>
              <p>Image preview not available</p>
            </div>
          </div>

          <!-- Video Preview -->
          <div v-else-if="isVideo" class="media-preview">
            <video
              v-if="currentMediaUrl"
              ref="mediaPlayerRef"
              :src="currentMediaUrl"
              controls
              class="preview-video"
              :key="currentMediaUrl"
              @error="handleMediaError"
              @loadeddata="handleMediaLoad"
              @timeupdate="handleTimeUpdate"
            >
              Your browser does not support the video tag.
            </video>
            <div v-else-if="fileData.thumbnail_url" class="thumbnail-fallback">
              <img
                :src="fileData.thumbnail_url"
                :alt="fileData.file_id"
                class="preview-thumbnail"
              />
              <p class="fallback-text">Video not available, showing thumbnail</p>
            </div>
            <div v-else class="no-preview">
              <span class="no-preview-icon">🎬</span>
              <p>Video preview not available</p>
            </div>
          </div>

          <!-- Audio Preview -->
          <div v-else-if="isAudio" class="media-preview">
            <div v-if="currentMediaUrl" class="audio-player-container">
              <div class="audio-icon">🎵</div>
              <audio
                ref="mediaPlayerRef"
                :src="currentMediaUrl"
                controls
                class="preview-audio"
                :key="currentMediaUrl"
                @error="handleMediaError"
                @loadeddata="handleMediaLoad"
                @timeupdate="handleTimeUpdate"
              >
                Your browser does not support the audio tag.
              </audio>
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

        <!-- Status indicator -->
        <div class="preview-status">
          <span v-if="!hasAnnotatedFile && hasOriginalFile" class="status-processing">
            <span class="pulse-dot"></span>
            Processing with AI... Annotated file will appear when ready
          </span>
          <span v-else-if="showAnnotated && hasAnnotatedFile" class="status-annotated">
            Showing AI-annotated version with detected objects highlighted
          </span>
          <span v-else-if="!showAnnotated && hasOriginalFile" class="status-original">
            Showing original uploaded file
          </span>
        </div>

        <!-- Species Timeline (Gantt Chart) - Only show for audio/video with tags_timestemp -->
        <div v-if="(isVideo || isAudio) && hasTimelineData" class="timeline-section">
          <div class="timeline-header">
            <h3>🎯 Species Detection Timeline</h3>
            <div class="timeline-legend">
              <span class="legend-item">
                <span class="legend-color current"></span>
                Current position
              </span>
              <span class="legend-hint">Click on any bar to jump to that time</span>
            </div>
          </div>
          
          <!-- Timeline Container with two columns -->
          <div class="timeline-container">
            <!-- Left column: labels -->
            <div class="timeline-labels-column">
              <div class="axis-label-spacer"></div>
              <div 
                v-for="species in timelineSpecies" 
                :key="'label-' + species.name"
                class="species-label"
                :title="species.name"
              >
                {{ species.name }}
              </div>
            </div>

            <!-- Right column: time axis and bars -->
            <div class="timeline-bars-column">
              <!-- Time axis header -->
              <div class="axis-ticks">
                <span 
                  v-for="tick in timelineTicks" 
                  :key="tick.time"
                  class="tick-label"
                  :style="{ left: tick.position + '%' }"
                >
                  {{ tick.label }}
                </span>
              </div>

              <!-- Bars area with current time indicator -->
              <div class="timeline-bars-area">
                <!-- Current time indicator - now inside the bars area -->
                <div 
                  class="current-time-indicator" 
                  :style="{ left: currentTimePosition + '%' }"
                  v-if="currentTimePosition >= 0"
                ></div>

                <!-- Species bars rows -->
                <div 
                  v-for="species in timelineSpecies" 
                  :key="'bars-' + species.name"
                  class="species-bars"
                >
                  <div
                    v-for="(segment, idx) in species.segments"
                    :key="idx"
                    class="segment-bar"
                    :class="{ 'is-playing': isSegmentPlaying(segment) }"
                    :style="{
                      left: segment.startPercent + '%',
                      width: segment.widthPercent + '%',
                      backgroundColor: species.color
                    }"
                    :title="`${species.name}: ${segment.startTime} - ${segment.endTime}`"
                    @click="seekToTime(segment.startSeconds)"
                  >
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- File Information Section -->
      <div class="info-wrapper">
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
              <span>🏷️</span> Open Annotated File
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
import { ref, onMounted, onUnmounted, computed } from 'vue'
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
const showAnnotated = ref(true) // Default to showing annotated file

// Media player refs
const mediaPlayerRef = ref(null)
const currentPlayTime = ref(0)
const mediaDuration = ref(0)

// Species colors for the timeline
const speciesColors = [
  '#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#E91E63',
  '#00BCD4', '#8BC34A', '#FF5722', '#673AB7', '#3F51B5',
  '#009688', '#FFC107', '#795548', '#607D8B', '#F44336'
]

// File type helpers
const isImage = computed(() => {
  const type = fileData.value.file_type?.toLowerCase()
  return type === 'image'
})

const isVideo = computed(() => {
  const type = fileData.value.file_type?.toLowerCase()
  return type === 'video'
})

const isAudio = computed(() => {
  const type = fileData.value.file_type?.toLowerCase()
  return type === 'audio'
})

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

const hasOriginalFile = computed(() => {
  return !!fileData.value.s3_url
})

const hasAnyFile = computed(() => {
  return hasAnnotatedFile.value || hasOriginalFile.value
})

// Get current media URL based on toggle state
// Priority: if showAnnotated is true and annotated exists, show annotated
// Otherwise show original if available
const currentMediaUrl = computed(() => {
  if (showAnnotated.value && hasAnnotatedFile.value) {
    return fileData.value.annotated_output_url
  }
  return fileData.value.s3_url || null
})

const isProcessing = computed(() => {
  return !hasTags.value && (!fileData.value.thumbnail_url || !fileData.value.s3_url)
})

// ========== Timeline (Gantt Chart) Related ==========

// Parse time string (HH:MM:SS or MM:SS) to seconds
const parseTimeToSeconds = (timeStr) => {
  if (!timeStr) return 0
  const parts = timeStr.split(':').map(Number)
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  } else if (parts.length === 2) {
    return parts[0] * 60 + parts[1]
  }
  return 0
}

// Format seconds to MM:SS or HH:MM:SS
const formatSecondsToTime = (seconds) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

// Parse DynamoDB format tags_timestemp to normalized array
const parsedTimelineData = computed(() => {
  const rawData = fileData.value.tags_timestemp
  if (!rawData || !Array.isArray(rawData)) return []
  
  return rawData.map(item => {
    // Handle DynamoDB format: { M: { species: { S: "..." }, start_time: { S: "..." }, ... } }
    const data = item.M || item
    
    const species = data.species?.S || data.species || ''
    const startTime = data.start_time?.S || data.start_time || ''
    const endTime = data.end_time?.S || data.end_time || ''
    
    return {
      species,
      startTime,
      endTime,
      startSeconds: parseTimeToSeconds(startTime),
      endSeconds: parseTimeToSeconds(endTime)
    }
  }).filter(item => item.species && item.startSeconds < item.endSeconds)
})

// Check if we have valid timeline data
const hasTimelineData = computed(() => {
  return parsedTimelineData.value.length > 0
})

// Calculate total duration from timeline data
const timelineDuration = computed(() => {
  if (!hasTimelineData.value) return 0
  
  // Use media duration if available, otherwise calculate from data
  if (mediaDuration.value > 0) {
    return mediaDuration.value
  }
  
  const maxEnd = Math.max(...parsedTimelineData.value.map(item => item.endSeconds))
  // Add 10% padding
  return Math.ceil(maxEnd * 1.1)
})

// Group timeline data by species with segments
const timelineSpecies = computed(() => {
  if (!hasTimelineData.value) return []
  
  const speciesMap = new Map()
  const duration = timelineDuration.value || 1
  
  parsedTimelineData.value.forEach(item => {
    if (!speciesMap.has(item.species)) {
      speciesMap.set(item.species, {
        name: item.species,
        segments: [],
        color: ''
      })
    }
    
    const speciesData = speciesMap.get(item.species)
    speciesData.segments.push({
      startTime: item.startTime,
      endTime: item.endTime,
      startSeconds: item.startSeconds,
      endSeconds: item.endSeconds,
      startPercent: (item.startSeconds / duration) * 100,
      widthPercent: ((item.endSeconds - item.startSeconds) / duration) * 100
    })
  })
  
  // Convert to array and assign colors
  const result = Array.from(speciesMap.values())
  result.forEach((species, index) => {
    species.color = speciesColors[index % speciesColors.length]
    // Sort segments by start time
    species.segments.sort((a, b) => a.startSeconds - b.startSeconds)
  })
  
  // Sort species by first appearance
  result.sort((a, b) => {
    const aFirst = a.segments[0]?.startSeconds || 0
    const bFirst = b.segments[0]?.startSeconds || 0
    return aFirst - bFirst
  })
  
  return result
})

// Generate time axis ticks
const timelineTicks = computed(() => {
  const duration = timelineDuration.value
  if (duration <= 0) return []
  
  const ticks = []
  let interval = 30 // 30 seconds default
  
  if (duration > 600) interval = 120 // 2 minutes for > 10 min
  else if (duration > 300) interval = 60 // 1 minute for > 5 min
  else if (duration > 120) interval = 30 // 30 seconds for > 2 min
  else interval = 15 // 15 seconds for short clips
  
  for (let t = 0; t <= duration; t += interval) {
    ticks.push({
      time: t,
      label: formatSecondsToTime(t),
      position: (t / duration) * 100
    })
  }
  
  return ticks
})

// Current time position as percentage
const currentTimePosition = computed(() => {
  const duration = timelineDuration.value
  if (duration <= 0 || currentPlayTime.value < 0) return -1
  return (currentPlayTime.value / duration) * 100
})

// Check if a segment is currently playing
const isSegmentPlaying = (segment) => {
  return currentPlayTime.value >= segment.startSeconds && 
         currentPlayTime.value < segment.endSeconds
}

// Seek media to specific time
const seekToTime = (seconds) => {
  if (mediaPlayerRef.value) {
    mediaPlayerRef.value.currentTime = seconds
    // Also start playing if paused
    if (mediaPlayerRef.value.paused) {
      mediaPlayerRef.value.play()
    }
  }
}

// Handle time update from media player
const handleTimeUpdate = () => {
  if (mediaPlayerRef.value) {
    currentPlayTime.value = mediaPlayerRef.value.currentTime
    if (!mediaDuration.value && mediaPlayerRef.value.duration) {
      mediaDuration.value = mediaPlayerRef.value.duration
    }
  }
}

// ========== End Timeline Related ==========

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

// Open current displayed media in new tab
const openCurrentInNewTab = () => {
  if (currentMediaUrl.value) {
    window.open(currentMediaUrl.value, '_blank')
  }
}

// Unified media error handler
const handleMediaError = (e) => {
  const isAnnotated = showAnnotated.value && hasAnnotatedFile.value
  console.error(`Failed to load ${isAnnotated ? 'annotated' : 'original'} media:`, currentMediaUrl.value, e)
  
  // If annotated file fails to load, fall back to original
  if (isAnnotated && hasOriginalFile.value) {
    console.log('Falling back to original file...')
    showAnnotated.value = false
  }
}

// Media load success handler
const handleMediaLoad = () => {
  console.log('Media loaded successfully:', showAnnotated.value ? 'annotated' : 'original')
}

// Toggle play/pause for media player
const togglePlayPause = () => {
  if (mediaPlayerRef.value) {
    if (mediaPlayerRef.value.paused) {
      mediaPlayerRef.value.play()
    } else {
      mediaPlayerRef.value.pause()
    }
  }
}

// Keyboard event handler for spacebar
const handleKeydown = (event) => {
  // Only handle spacebar
  if (event.code === 'Space' || event.key === ' ') {
    // Don't trigger if user is typing in an input/textarea
    const activeElement = document.activeElement
    const isInputFocused = activeElement && (
      activeElement.tagName === 'INPUT' ||
      activeElement.tagName === 'TEXTAREA' ||
      activeElement.isContentEditable
    )
    
    if (!isInputFocused && (isVideo.value || isAudio.value) && currentMediaUrl.value) {
      event.preventDefault() // Prevent page scroll
      togglePlayPause()
    }
  }
}

const goBack = () => {
  router.push('/dashboard')
}

const handleSignOut = () => {
  websocketService.disconnect()
  authService.globalSignOut()
}

onMounted(async () => {
  // Add keyboard event listener for spacebar play/pause
  window.addEventListener('keydown', handleKeydown)
  
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

onUnmounted(() => {
  // Remove keyboard event listener
  window.removeEventListener('keydown', handleKeydown)
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 30px;
}

section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 30px;
}

.preview-section {
  display: flex;
  flex-direction: column;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.preview-header h2 {
  margin: 0;
  font-size: 1.4rem;
  color: #333;
  font-weight: 600;
}

.ai-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Toggle Switch Styles */
.toggle-container {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: #f5f7fa;
  border-radius: 24px;
}

.toggle-label-text {
  font-size: 0.85rem;
  color: #999;
  font-weight: 500;
  transition: color 0.3s;
}

.toggle-label-text.active {
  color: #667eea;
  font-weight: 600;
}

.toggle-switch-wrapper {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  cursor: pointer;
}

.toggle-input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #ccc;
  border-radius: 13px;
  transition: background 0.3s;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: transform 0.3s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-input:checked + .toggle-slider {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.toggle-input:checked + .toggle-slider::before {
  transform: translateX(22px);
}

.btn-open-new-tab {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 2px solid #667eea;
  background: white;
  color: #667eea;
  font-size: 1.2rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.btn-open-new-tab:hover {
  background: #667eea;
  color: white;
}

.preview-container {
  width: 100%;
  flex: 1;
}

/* Loading Preview State */
.loading-preview {
  padding: 80px 40px;
  text-align: center;
  color: #666;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

.loading-preview p {
  font-size: 1.1rem;
  font-weight: 500;
  margin: 0 0 8px 0;
  color: #333;
}

.loading-hint {
  font-size: 0.9rem;
  color: #999;
}

/* Preview Status Indicator */
.preview-status {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 0.85rem;
}

.status-processing {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e65100;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: #e65100;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.status-annotated {
  color: #667eea;
}

.status-original {
  color: #666;
}

/* ========== Timeline (Gantt Chart) Styles ========== */
.timeline-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 2px solid #f0f0f0;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.timeline-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #333;
  font-weight: 600;
}

.timeline-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 0.8rem;
  color: #666;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-color.current {
  background: #ff4444;
}

.legend-hint {
  color: #999;
  font-style: italic;
}

.timeline-container {
  display: flex;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  gap: 0;
}

/* Left column: species labels */
.timeline-labels-column {
  flex-shrink: 0;
  width: 120px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.axis-label-spacer {
  height: 24px;
  flex-shrink: 0;
}

.species-label {
  height: 24px;
  line-height: 24px;
  padding-right: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #444;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Right column: time axis and bars */
.timeline-bars-column {
  flex: 1;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* Time axis at the top */
.axis-ticks {
  position: relative;
  height: 24px;
  border-bottom: 1px solid #ddd;
  flex-shrink: 0;
}

.tick-label {
  position: absolute;
  transform: translateX(-50%);
  font-size: 0.7rem;
  color: #888;
  white-space: nowrap;
  top: 4px;
}

/* Bars area container */
.timeline-bars-area {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* Current time indicator - now inside bars area */
.current-time-indicator {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ff4444;
  z-index: 10;
  pointer-events: none;
  transform: translateX(-1px);
}

.current-time-indicator::before {
  content: '';
  position: absolute;
  top: -6px;
  left: -4px;
  width: 10px;
  height: 10px;
  background: #ff4444;
  border-radius: 50%;
}

/* Species bars row */
.species-bars {
  position: relative;
  height: 24px;
  background: #f0f0f0;
  border-radius: 4px;
}

.segment-bar {
  position: absolute;
  top: 2px;
  height: 20px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
  opacity: 0.85;
  min-width: 4px;
}

.segment-bar:hover {
  opacity: 1;
  transform: scaleY(1.15);
  z-index: 5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.segment-bar.is-playing {
  opacity: 1;
  box-shadow: 0 0 0 2px #ff4444, 0 2px 8px rgba(255, 68, 68, 0.4);
  z-index: 6;
}

/* ========== End Timeline Styles ========== */

.info-wrapper {
  max-width: 1200px;
  margin: 0 auto;
}

.media-preview {
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: #f5f5f5;
}

.preview-image {
  width: 100%;
  height: auto;
  display: block;
}

.preview-video {
  width: 100%;
  height: auto;
  display: block;
  max-height: 80vh; /* 限制视频最大高度为屏幕高度的 80% */
  object-fit: contain; /* 保持视频比例 */
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

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
  }

  .page-title {
    font-size: 1.4rem;
  }

  .details-main {
    padding: 20px 15px;
  }

  section {
    padding: 20px;
  }

  .preview-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .toggle-container {
    padding: 6px 12px;
  }

  .toggle-label-text {
    font-size: 0.8rem;
  }

  .preview-header h2 {
    font-size: 1.1rem;
  }

  /* Timeline responsive styles */
  .timeline-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .timeline-legend {
    flex-wrap: wrap;
    gap: 8px;
  }

  .timeline-labels-column {
    width: 80px;
  }

  .species-label {
    font-size: 0.7rem;
  }

  .tick-label {
    font-size: 0.6rem;
  }

  .timeline-container {
    padding: 12px;
  }

  .timeline-bars-column {
    min-width: 200px;
  }

  .actions-section {
    flex-direction: column;
  }

  .actions-section .btn {
    width: 100%;
    justify-content: center;
  }

  .info-grid {
    gap: 15px;
  }

  .preview-status {
    font-size: 0.8rem;
    padding: 10px 12px;
  }
}
</style>

