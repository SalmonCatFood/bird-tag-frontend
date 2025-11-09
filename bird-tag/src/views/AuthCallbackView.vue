<template>
  <div class="auth-callback-container">
    <div class="callback-card">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <h2>Authenticating...</h2>
        <p>Please wait while we complete your sign in.</p>
      </div>

      <div v-else-if="error" class="error-state">
        <div class="error-icon">⚠️</div>
        <h2>Authentication Failed</h2>
        <p>{{ error }}</p>
        <button @click="goToLogin" class="btn btn-primary">
          Back to Login
        </button>
      </div>

      <div v-else class="success-state">
        <div class="success-icon">✓</div>
        <h2>Authentication Successful</h2>
        <p>Redirecting to dashboard...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import authService from '@/services/authService'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const error = ref('')

const goToLogin = () => {
  router.push('/login')
}

onMounted(async () => {
  try {
    // Check for OAuth authorization code
    const code = route.query.code
    const errorParam = route.query.error
    const errorDescription = route.query.error_description

    if (errorParam) {
      throw new Error(errorDescription || errorParam)
    }

    if (code) {
      // Handle OAuth callback
      await authService.handleOAuthCallback(code)
      loading.value = false
      
      // Redirect to dashboard after short delay
      setTimeout(() => {
        router.push('/dashboard')
      }, 1500)
    } else {
      // No code found, check if already authenticated
      const isAuth = await authService.isAuthenticated()
      if (isAuth) {
        router.push('/dashboard')
      } else {
        throw new Error('No authorization code received')
      }
    }
  } catch (err) {
    console.error('Auth callback error:', err)
    error.value = err.message || 'Authentication failed. Please try again.'
    loading.value = false
  }
})
</script>

<style scoped>
.auth-callback-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.callback-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 100%;
  padding: 60px 40px;
  text-align: center;
}

.loading-state,
.error-state,
.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  font-size: 4rem;
  color: #f44336;
}

.success-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #4caf50;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
  font-weight: bold;
}

h2 {
  margin: 0;
  font-size: 1.8rem;
  color: #333;
}

p {
  margin: 0;
  color: #666;
  font-size: 1rem;
}

.btn {
  padding: 12px 32px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 10px;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}
</style>

