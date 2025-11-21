<template>
  <div class="relative">
    <button 
      @click="isOpen = !isOpen"
      class="glass-button flex items-center px-4 py-2 shadow-sm relative"
    >
      <AppIcon icon="lucide:bell" size="16" class="mr-2" />
      Notifications
      <span 
        v-if="unreadCount > 0"
        class="absolute -top-1 -right-1 bg-destructive text-destructive-foreground text-xs rounded-full h-5 w-5 flex items-center justify-center"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Dropdown -->
    <div 
      v-if="isOpen"
      class="absolute right-0 mt-2 w-80 glass-card p-4 z-50 animate-fade-in"
    >
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold">Notifications</h3>
        <div class="flex items-center space-x-2">
          <button 
            v-if="unreadCount > 0"
            @click="markAllAsRead"
            class="text-xs text-primary hover:text-primary/80"
          >
            Mark all read
          </button>
          <button 
            @click="isOpen = false"
            class="text-muted-foreground hover:text-foreground"
          >
            <AppIcon icon="lucide:x" size="16" />
          </button>
        </div>
      </div>

      <div v-if="notifications.length === 0" class="text-center py-8">
        <AppIcon icon="lucide:bell-off" size="48" class="mx-auto text-muted-foreground mb-4" />
        <p class="text-muted-foreground">No notifications</p>
      </div>

      <div v-else class="space-y-3 max-h-80 overflow-y-auto">
        <div 
          v-for="notification in notifications.slice(0, 10)" 
          :key="notification.id"
          @click="handleNotificationClick(notification)"
          class="flex items-start space-x-3 p-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
          :class="{ 'bg-muted/30': !notification.read }"
        >
          <div class="flex-shrink-0 mt-1">
            <div 
              class="w-2 h-2 rounded-full"
              :class="getNotificationTypeColor(notification.type)"
            />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-foreground">
              {{ notification.title }}
            </p>
            <p class="text-xs text-muted-foreground mt-1">
              {{ notification.message }}
            </p>
            <p class="text-xs text-muted-foreground mt-1">
              {{ formatTime(notification.created_at || notification.timestamp) }}
            </p>
            <p v-if="notification.media_title" class="text-xs text-muted-foreground mt-1">
              {{ notification.media_type === 'movie' ? 'Movie' : 'TV Show' }}: {{ notification.media_title }}
            </p>
          </div>
          <button 
            @click="removeNotification(notification.id)"
            class="text-muted-foreground hover:text-destructive transition-colors"
          >
            <AppIcon icon="lucide:x" size="14" />
          </button>
        </div>
      </div>

      <div v-if="notifications.length > 10" class="text-center pt-4 border-t border-border">
        <button class="text-sm text-primary hover:text-primary/80">
          View all notifications
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from '~/composables/useNotifications'
import { onClickOutside } from '@vueuse/core'

const { notifications, unreadCount, markAllAsRead, removeNotification, markAsRead, fetchNotifications } = useNotifications()

const isOpen = ref(false)

const getNotificationTypeColor = (type: string) => {
  const colors = {
    success: 'bg-success',
    error: 'bg-destructive',
    warning: 'bg-warning',
    info: 'bg-info'
  }
  return colors[type as keyof typeof colors] || 'bg-muted-foreground'
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString()
}

const handleNotificationClick = async (notification: any) => {
  if (!notification.read) {
    await markAsRead(notification.id)
  }
}

// Close dropdown when clicking outside
onClickOutside(isOpen, () => {
  isOpen.value = false
})

// Fetch notifications when dropdown opens
watch(isOpen, async (newValue) => {
  if (newValue) {
    await fetchNotifications(50, false)
  }
})
</script>
