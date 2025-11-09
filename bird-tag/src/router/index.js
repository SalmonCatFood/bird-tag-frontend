/**
 * Vue Router Configuration
 * Handles application routing with authentication guards
 */

import { createRouter, createWebHistory } from 'vue-router'
import authService from '@/services/authService'

// Views
import LoginView from '@/views/LoginView.vue'
import AuthCallbackView from '@/views/AuthCallbackView.vue'
import DashboardView from '@/views/DashboardView.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresGuest: true },
  },
  {
    path: '/auth',
    name: 'AuthCallback',
    component: AuthCallbackView,
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const requiresGuest = to.matched.some(record => record.meta.requiresGuest)
  
  try {
    const isAuthenticated = await authService.isAuthenticated()
    
    if (requiresAuth && !isAuthenticated) {
      // Redirect to login if trying to access protected route
      next('/login')
    } else if (requiresGuest && isAuthenticated) {
      // Redirect to dashboard if trying to access login while authenticated
      next('/dashboard')
    } else {
      next()
    }
  } catch (error) {
    console.error('Navigation guard error:', error)
    if (requiresAuth) {
      next('/login')
    } else {
      next()
    }
  }
})

export default router

