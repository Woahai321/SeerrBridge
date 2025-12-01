<template>
  <div class="fixed top-4 right-4 z-[9999] space-y-2 max-h-[calc(100vh-2rem)] overflow-hidden pointer-events-none">
    <TransitionGroup name="notification" tag="div" class="flex flex-col-reverse space-y-reverse space-y-2">
      <div
        v-for="notification in displayedNotifications"
        :key="notification.id"
        class="glass-card p-4 max-w-sm animate-fade-in pointer-events-auto shadow-lg border"
        :class="getNotificationClass(notification.type)"
      >
        <div class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <AppIcon 
              :icon="getNotificationIcon(notification.type)" 
              size="18" 
              :class="getNotificationIconClass(notification.type)"
            />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-foreground">
              {{ notification.title }}
            </p>
            <p class="text-xs text-muted-foreground mt-1 line-clamp-2">
              {{ notification.message }}
            </p>
            <p v-if="notification.media_title" class="text-xs text-muted-foreground mt-1 line-clamp-1">
              {{ notification.media_type === 'movie' ? 'Movie' : 'TV Show' }}: {{ notification.media_title }}
            </p>
          </div>
          <button 
            @click="removeNotification(notification.id)"
            class="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1 -mt-1 -mr-1"
            aria-label="Close notification"
          >
            <AppIcon icon="lucide:x" size="18" />
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from '~/composables/useNotifications'
import type { Notification } from '~/composables/useNotifications'

const { notifications, removeNotification, startPolling, initializeNotifications } = useNotifications()

// Maximum number of toasts to display at once
const MAX_DISPLAYED_TOASTS = 5

// Timeout durations in milliseconds based on notification type
const TOAST_DURATIONS = {
  success: 4000,  // 4 seconds
  info: 5000,     // 5 seconds
  warning: 6000,  // 6 seconds
  error: 8000     // 8 seconds (errors stay longer)
}

// Track active timeouts for each notification
const notificationTimeouts = new Map<string | number, NodeJS.Timeout>()

// Computed property to limit displayed notifications
const displayedNotifications = computed(() => {
  return notifications.value.slice(0, MAX_DISPLAYED_TOASTS)
})

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

// Setup auto-dismiss timeout for a notification
const setupAutoDismiss = (notification: Notification) => {
  // Clear any existing timeout for this notification
  const notificationId = String(notification.id)
  const existingTimeout = notificationTimeouts.get(notificationId)
  if (existingTimeout) {
    clearTimeout(existingTimeout)
  }

  // Get duration based on notification type
  const duration = TOAST_DURATIONS[notification.type] || TOAST_DURATIONS.info

  // Set up new timeout
  const timeout = setTimeout(() => {
    removeNotification(notification.id)
    notificationTimeouts.delete(notificationId)
  }, duration)

  notificationTimeouts.set(notificationId, timeout)
}

// Set up auto-dismiss for all displayed notifications
const setupAllDisplayedNotifications = () => {
  displayedNotifications.value.forEach(notification => {
    const notificationId = String(notification.id)
    // Set up timer if not already set up
    if (!notificationTimeouts.has(notificationId)) {
      setupAutoDismiss(notification)
    }
  })
  
  // Clean up timeouts for notifications that are no longer displayed
  const displayedIds = new Set(displayedNotifications.value.map(n => String(n.id)))
  notificationTimeouts.forEach((timeout, id) => {
    if (!displayedIds.has(String(id))) {
      clearTimeout(timeout)
      notificationTimeouts.delete(id)
    }
  })
}

// Watch displayed notifications and set up auto-dismiss
watch(displayedNotifications, () => {
  setupAllDisplayedNotifications()
}, { immediate: true, deep: true })

// Also watch the full notifications list to catch when new ones are added
watch(notifications, () => {
  nextTick(() => {
    setupAllDisplayedNotifications()
  })
}, { deep: true })

// Clean up on unmount
onMounted(async () => {
  // Initialize notifications on startup FIRST (this sets pageLoadTime)
  await initializeNotifications()
  
  // Wait a bit to ensure initialization is complete before starting polling
  await nextTick()
  
  // Set up auto-dismiss for all displayed notifications after initialization
  setupAllDisplayedNotifications()
  
  // Periodic check to ensure all displayed notifications have timers (safety net)
  const checkInterval = setInterval(() => {
    setupAllDisplayedNotifications()
  }, 2000) // Check every 2 seconds
  
  // Start ultra real-time notification polling AFTER initialization
  // This ensures pageLoadTime is set before any notifications are fetched
  const stopPolling = startPolling(1000) // Ultra real-time: Poll every 1 second

  onUnmounted(() => {
    // Clear all timeouts and intervals
    clearInterval(checkInterval)
    notificationTimeouts.forEach(timeout => clearTimeout(timeout))
    notificationTimeouts.clear()
    stopPolling()
  })
})
</script>

<style scoped>
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%) scale(0.95);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%) scale(0.95);
}

.notification-move {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
