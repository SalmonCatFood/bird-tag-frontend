<template>
  <div class="callback-container">
    <div class="callback-card">
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>正在处理登录...</p>
      </div>
      <div v-else-if="error" class="error">
        <h2>登录失败</h2>
        <p>{{ error }}</p>
        <button @click="goToLogin" class="retry-button">返回登录页</button>
      </div>
      <div v-else class="success">
        <h2>登录成功</h2>
        <p>正在跳转...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { handleOAuthCallback } from '@/services/auth'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    // 从 URL 查询参数中获取 code
    const code = route.query.code
    const state = route.query.state
    
    if (!code) {
      throw new Error('未找到授权码')
    }

    // 验证 state（防止 CSRF 攻击）
    const savedState = sessionStorage.getItem('oauth_state')
    if (state && savedState && state !== savedState) {
      throw new Error('State 验证失败')
    }
    sessionStorage.removeItem('oauth_state')

    // 处理 OAuth 回调
    await handleOAuthCallback(code)

    // 登录成功，跳转到上传页面
    setTimeout(() => {
      router.push('/upload')
    }, 1000)
  } catch (err) {
    console.error('OAuth 回调处理错误:', err)
    error.value = err.message || '登录失败，请重试'
    loading.value = false
  }
})

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.callback-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.callback-card {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error h2 {
  color: #c33;
  margin-bottom: 15px;
}

.error p {
  color: #666;
  margin-bottom: 20px;
}

.success h2 {
  color: #3c3;
  margin-bottom: 15px;
}

.success p {
  color: #666;
}

.retry-button {
  padding: 12px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.3s;
}

.retry-button:hover {
  background: #5568d3;
}
</style>

