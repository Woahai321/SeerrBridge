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
            @click="handleManualDismiss(notification.id)"
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

const { notifications, removeNotification, startPolling, initializeNotifications, markAsRead } = useNotifications()

// Maximum number of toasts to display at once (single notification queue)
const MAX_DISPLAYED_TOASTS = 1

// Timeout durations in milliseconds based on notification type (faster dismiss)
const TOAST_DURATIONS = {
  success: 2000,  // 2 seconds
  info: 2500,     // 2.5 seconds
  warning: 3000,  // 3 seconds
  error: 4000     // 4 seconds (errors stay longer but still faster)
}

// Track active timeouts for each notification
const notificationTimeouts = new Map<string | number, NodeJS.Timeout>()

// Track currently displayed notification ID for queue management
const currentDisplayedId = ref<string | number | null>(null)

// Computed property to show only the first unread notification (queue system)
const displayedNotifications = computed(() => {
  // Filter to only unread notifications
  const unreadNotifications = notifications.value.filter(n => !n.read)
  
  // If we have a currently displayed notification, keep showing it until it's removed
  if (currentDisplayedId.value !== null) {
    const current = unreadNotifications.find(n => String(n.id) === String(currentDisplayedId.value))
    if (current) {
      return [current]
    }
    // Current notification was removed, clear the reference
    currentDisplayedId.value = null
  }
  
  // Show the first unread notification (queue system)
  if (unreadNotifications.length > 0) {
    const nextNotification = unreadNotifications[0]
    currentDisplayedId.value = nextNotification.id
    return [nextNotification]
  }
  
  // No unread notifications
  currentDisplayedId.value = null
  return []
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
    // Mark as read when auto-dismissing
    markAsRead(notification.id)
    removeNotification(notification.id)
    notificationTimeouts.delete(notificationId)
    
    // Clear current displayed ID to trigger next notification in queue
    if (currentDisplayedId.value === notification.id) {
      currentDisplayedId.value = null
    }
    
    // Trigger next notification in queue after a brief delay for smooth transition
    nextTick(() => {
      // The computed property will automatically show the next notification
    })
  }, duration)

  notificationTimeouts.set(notificationId, timeout)
}

// Handle manual dismissal (user clicks X button)
const handleManualDismiss = (id: string | number) => {
  // Clear timeout if exists
  const notificationId = String(id)
  const timeout = notificationTimeouts.get(notificationId)
  if (timeout) {
    clearTimeout(timeout)
    notificationTimeouts.delete(notificationId)
  }
  
  // Mark as read and remove
  markAsRead(id)
  removeNotification(id)
  
  // Clear current displayed ID to trigger next notification in queue
  if (currentDisplayedId.value === id) {
    currentDisplayedId.value = null
  }
  
  // Trigger next notification in queue after a brief delay for smooth transition
  nextTick(() => {
    // The computed property will automatically show the next notification
  })
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
  
  // Start notification polling AFTER initialization
  // This ensures pageLoadTime is set before any notifications are fetched
  const stopPolling = startPolling(2000) // Poll every 2 seconds (reduced from 1 second)

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
