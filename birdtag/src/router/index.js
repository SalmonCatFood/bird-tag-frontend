import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '@/utils/auth'
import { checkAuthStatus } from '@/services/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/upload'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/auth/callback',
      name: 'AuthCallback',
      component: () => import('@/views/AuthCallback.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/upload',
      name: 'Upload',
      component: () => import('@/views/Upload.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/files',
      name: 'Files',
      component: () => import('@/views/Files.vue'),
      meta: { requiresAuth: true }
    }
  ],
})

// 路由守卫：检查认证状态
router.beforeEach(async (to, from, next) => {
  // OAuth 回调页面不需要检查认证
  if (to.path === '/auth/callback') {
    next()
    return
  }

  // 检查是否需要认证
  if (to.meta.requiresAuth) {
    // 先快速检查本地 token
    if (!isAuthenticated()) {
      next('/login')
      return
    }
    
    // 可选：进一步验证 token 有效性（异步）
    // 注意：这会增加延迟，如果不需要可以移除
    try {
      const isValid = await checkAuthStatus()
      if (!isValid) {
        next('/login')
        return
      }
    } catch {
      // 如果检查失败，使用本地检查结果
    }
  }

  // 如果已登录且访问登录页，重定向到上传页
  if (to.path === '/login' && isAuthenticated()) {
    next('/upload')
    return
  }

  next()
})

export default router
