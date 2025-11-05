<template>
  <div class="files-container">
    <div class="files-header">
      <h1>我的文件</h1>
      <button @click="goToUpload" class="upload-button">+ 上传新文件</button>
    </div>

    <div v-if="loading" class="loading">
      加载中...
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-if="!loading && files.length === 0" class="empty-state">
      <p>还没有上传任何文件</p>
      <button @click="goToUpload" class="upload-button">立即上传</button>
    </div>

    <div v-if="files.length > 0" class="files-grid">
      <div v-for="file in files" :key="file.file_id" class="file-card">
        <div class="file-thumbnail">
          <img
            v-if="file.thumbnail_url"
            :src="file.thumbnail_url"
            :alt="file.file_id"
            @error="handleImageError"
          />
          <div v-else class="no-thumbnail">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
          </div>
        </div>

        <div class="file-info">
          <div class="file-type-badge" :class="file.file_type">
            {{ file.file_type }}
          </div>
          <p class="file-id">{{ file.file_id }}</p>
          <p class="file-time">{{ formatTime(file.upload_timestamp) }}</p>
        </div>

        <div v-if="Object.keys(file.tags || {}).length > 0" class="file-tags">
          <div
            v-for="(count, species) in file.tags"
            :key="species"
            class="tag"
          >
            {{ species }} ({{ count }})
          </div>
        </div>
        <div v-else class="no-tags">
          处理中...
        </div>

        <div class="file-actions">
          <button @click="viewFile(file)" class="view-button">查看详情</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getFileMetadata } from '@/utils/api'

const router = useRouter()
const files = ref([])
const loading = ref(false)
const error = ref('')

const goToUpload = () => {
  router.push('/upload')
}

const viewFile = (file) => {
  // 可以导航到详情页，或显示模态框
  console.log('View file:', file)
  // router.push(`/file/${file.file_id}`)
}

const handleImageError = (event) => {
  event.target.style.display = 'none'
}

const formatTime = (timestamp) => {
  if (!timestamp) return '未知时间'
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN')
  } catch {
    return timestamp
  }
}

const loadFiles = async () => {
  loading.value = true
  error.value = ''

  try {
    // TODO: 实现获取文件列表的 API
    // 目前没有对应的 API 端点，需要后端添加 GET /files 或类似端点
    // 这里先使用空数组作为占位
    files.value = []
    
    // 示例：如果有 API，可以这样调用
    // const response = await fetch('/api/files')
    // files.value = await response.json()
  } catch (err) {
    error.value = err.message || '加载文件列表失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.files-container {
  min-height: 100vh;
  padding: 40px 20px;
  background: #f5f7fa;
}

.files-header {
  max-width: 1200px;
  margin: 0 auto 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.files-header h1 {
  margin: 0;
  color: #333;
}

.upload-button {
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.3s;
}

.upload-button:hover {
  background: #5568d3;
}

.loading,
.error-message {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  text-align: center;
}

.error-message {
  background: #fee;
  color: #c33;
  border-radius: 6px;
}

.empty-state {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state p {
  font-size: 18px;
  margin-bottom: 20px;
}

.files-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.file-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
}

.file-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.file-thumbnail {
  width: 100%;
  height: 200px;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.file-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-thumbnail {
  color: #999;
}

.file-info {
  padding: 15px;
}

.file-type-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 10px;
}

.file-type-badge.image {
  background: #e3f2fd;
  color: #1976d2;
}

.file-type-badge.video {
  background: #fce4ec;
  color: #c2185b;
}

.file-type-badge.audio {
  background: #f3e5f5;
  color: #7b1fa2;
}

.file-id {
  font-size: 12px;
  color: #999;
  margin: 5px 0;
  word-break: break-all;
}

.file-time {
  font-size: 12px;
  color: #666;
  margin: 5px 0;
}

.file-tags {
  padding: 0 15px 15px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  background: #667eea;
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.no-tags {
  padding: 0 15px 15px;
  color: #999;
  font-size: 12px;
  font-style: italic;
}

.file-actions {
  padding: 0 15px 15px;
}

.view-button {
  width: 100%;
  padding: 8px;
  background: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.3s;
}

.view-button:hover {
  background: #e0e0e0;
}
</style>

