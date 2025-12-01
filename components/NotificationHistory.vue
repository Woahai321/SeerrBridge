<template>
  <div class="relative" ref="containerRef">
    <button 
      @click="isOpen = !isOpen"
      class="glass-button flex items-center px-2 sm:px-4 py-1.5 sm:py-2 shadow-sm relative"
    >
      <AppIcon icon="lucide:bell" size="18" class="sm:mr-2 flex-shrink-0" />
      <span class="hidden sm:inline">Notifications</span>
      <span 
        v-if="unreadCount > 0"
        class="absolute -top-0.5 -right-0.5 sm:-top-1 sm:-right-1 bg-destructive text-destructive-foreground text-[10px] sm:text-xs rounded-full h-4 w-4 sm:h-5 sm:w-5 flex items-center justify-center"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <Teleport to="body">
      <!-- Mobile overlay -->
      <div 
        v-if="isOpen && isMobile"
        class="fixed inset-0 bg-black/50 z-[99998] sm:hidden"
        @click="isOpen = false"
      />
      
      <!-- Dropdown -->
      <div 
        v-if="isOpen"
        class="fixed z-[99999] inset-x-4 sm:inset-x-auto top-1/2 sm:top-auto sm:right-4 sm:mt-2 -translate-y-1/2 sm:translate-y-0 w-[calc(100vw-2rem)] sm:w-80 sm:max-w-none max-h-[85vh] sm:max-h-none glass-card p-3 sm:p-4 animate-fade-in overflow-hidden flex flex-col"
        :style="dropdownStyle"
      >
      <div class="flex items-center justify-between mb-3 sm:mb-4 flex-shrink-0">
        <h3 class="text-base sm:text-lg font-semibold">Notifications</h3>
        <div class="flex items-center space-x-2">
          <button 
            v-if="unreadCount > 0"
            @click="markAllAsRead"
            class="text-xs text-primary hover:text-primary/80 whitespace-nowrap"
          >
            <span class="hidden sm:inline">Mark all read</span>
            <span class="sm:hidden">Mark read</span>
          </button>
          <button 
            @click="isOpen = false"
            class="text-muted-foreground hover:text-foreground flex-shrink-0"
          >
            <AppIcon icon="lucide:x" size="18" />
          </button>
        </div>
      </div>

      <div v-if="notifications.length === 0" class="text-center py-6 sm:py-8 flex-shrink-0">
        <AppIcon icon="lucide:bell-off" size="48" class="mx-auto text-muted-foreground mb-3 sm:mb-4" />
        <p class="text-sm sm:text-base text-muted-foreground">No notifications</p>
      </div>

      <div v-else class="space-y-2 sm:space-y-3 overflow-y-auto flex-1 min-h-0">
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
            <AppIcon icon="lucide:x" size="16" />
          </button>
        </div>
      </div>

      <div v-if="notifications.length > 10" class="text-center pt-3 sm:pt-4 border-t border-border flex-shrink-0">
        <button class="text-xs sm:text-sm text-primary hover:text-primary/80">
          View all notifications
        </button>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from '~/composables/useNotifications'
import { onClickOutside } from '@vueuse/core'

const { notifications, unreadCount, markAllAsRead, removeNotification, markAsRead, fetchNotifications } = useNotifications()

const isOpen = ref(false)
const containerRef = ref<HTMLElement | null>(null)
const isMobile = ref(false)
const dropdownStyle = ref<Record<string, string>>({})

// Check if mobile on mount and resize
const checkMobile = () => {
  isMobile.value = window.innerWidth < 640
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  window.addEventListener('resize', updateDropdownPosition)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('resize', updateDropdownPosition)
})

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
onClickOutside(containerRef, () => {
  isOpen.value = false
})

// Calculate dropdown position
const updateDropdownPosition = () => {
  if (!isMobile.value && containerRef.value) {
    nextTick(() => {
      const rect = containerRef.value!.getBoundingClientRect()
      dropdownStyle.value = {
        top: `${rect.bottom + 8}px`,
        right: `${window.innerWidth - rect.right}px`,
        left: 'auto',
        transform: 'none'
      }
    })
  } else {
    dropdownStyle.value = {}
  }
}

// Fetch notifications when dropdown opens
watch(isOpen, async (newValue) => {
  if (newValue) {
    await fetchNotifications(50, false)
    updateDropdownPosition()
  }
})

</script>
