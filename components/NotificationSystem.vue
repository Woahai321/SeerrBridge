<template>
  <div class="fixed top-4 right-4 z-50 space-y-2">
    <TransitionGroup name="notification" tag="div">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="glass-card p-4 max-w-sm animate-fade-in"
        :class="getNotificationClass(notification.type)"
      >
        <div class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <AppIcon 
              :icon="getNotificationIcon(notification.type)" 
              size="20" 
              :class="getNotificationIconClass(notification.type)"
            />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-foreground">
              {{ notification.title }}
            </p>
            <p class="text-xs text-muted-foreground mt-1">
              {{ notification.message }}
            </p>
            <p v-if="notification.media_title" class="text-xs text-muted-foreground mt-1">
              {{ notification.media_type === 'movie' ? 'Movie' : 'TV Show' }}: {{ notification.media_title }}
            </p>
          </div>
          <button 
            @click="removeNotification(notification.id)"
            class="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors"
          >
            <AppIcon icon="lucide:x" size="16" />
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from '~/composables/useNotifications'

const { notifications, removeNotification, startPolling, initializeNotifications } = useNotifications()

const getNotificationClass = (type: string) => {
  const classes = {
    success: 'border-success/20 bg-success/5',
    error: 'border-destructive/20 bg-destructive/5',
    warning: 'border-warning/20 bg-warning/5',
    info: 'border-info/20 bg-info/5'
  }
  return classes[type as keyof typeof classes] || 'border-border/20 bg-background/5'
}

const getNotificationIcon = (type: string) => {
  const icons = {
    success: 'lucide:check-circle',
    error: 'lucide:alert-circle',
    warning: 'lucide:alert-triangle',
    info: 'lucide:info'
  }
  return icons[type as keyof typeof icons] || 'lucide:info'
}

const getNotificationIconClass = (type: string) => {
  const classes = {
    success: 'text-success',
    error: 'text-destructive',
    warning: 'text-warning',
    info: 'text-info'
  }
  return classes[type as keyof typeof classes] || 'text-muted-foreground'
}

// Auto-remove notifications after 5 seconds
onMounted(async () => {
  // Initialize notifications on startup
  await initializeNotifications()
  
  const interval = setInterval(() => {
    notifications.value.forEach(notification => {
      const timestamp = notification.created_at || notification.timestamp
      const age = Date.now() - new Date(timestamp).getTime()
      // Only auto-remove if already read, otherwise keep showing it until it's marked read
      if (age > 5000 && notification.read) {
        removeNotification(notification.id)
      }
    })
  }, 1000)

  // Start polling for notifications
  const stopPolling = startPolling(30000) // Poll every 30 seconds

  onUnmounted(() => {
    clearInterval(interval)
    stopPolling()
  })
})
</script>

<style scoped>
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
