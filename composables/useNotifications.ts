export interface Notification {
  id: string | number
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
  created_at?: string
  read: boolean
  media_id?: number | null
  media_type?: string | null
  media_title?: string | null
  old_status?: string | null
  new_status?: string | null
}

export const useNotifications = () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)
  const lastChecked = ref<Date>(new Date())
  const displayedNotificationIds = ref<Set<string | number>>(new Set())

  // Fetch notifications from backend
  const fetchNotifications = async (limit = 50, unreadOnly = false) => {
    try {
      const query = new URLSearchParams({
        limit: limit.toString(),
        unreadOnly: unreadOnly.toString()
      })
      
      const data = await $fetch<{ success: boolean; data: Notification[] }>(
        `/api/notifications?${query}`
      )
      
      if (data.success && data.data) {
        // Get existing notification IDs
        const existingIds = new Set(notifications.value.map(n => String(n.id)))
        
        // Filter out duplicates and only get truly new notifications
        const newNotifications = data.data.filter(n => {
          const notificationId = String(n.id)
          // Don't show toasts for read notifications
          if (n.read) {
            return false
          }
          // Check if already displayed
          if (displayedNotificationIds.value.has(notificationId)) {
            return false
          }
          // Check if already in local list
          if (existingIds.has(notificationId)) {
            return false
          }
          return true
        })
        
        // Update existing notifications if they exist (for read status updates)
        data.data.forEach(backendNotif => {
          const existingIndex = notifications.value.findIndex(n => String(n.id) === String(backendNotif.id))
          if (existingIndex !== -1) {
            // Update read status
            notifications.value[existingIndex].read = backendNotif.read
          }
        })
        
        // Add new notifications to the beginning
        if (newNotifications.length > 0) {
          notifications.value.unshift(...newNotifications)
          
          // Mark all new notifications as displayed regardless of read status
          // This prevents them from showing as toasts again on subsequent polls
          newNotifications.forEach(n => {
            displayedNotificationIds.value.add(String(n.id))
          })
        }
        
        // Sort by timestamp (newest first)
        notifications.value.sort((a, b) => {
          const dateA = new Date(a.created_at || a.timestamp).getTime()
          const dateB = new Date(b.created_at || b.timestamp).getTime()
          return dateB - dateA
        })
        
        // Keep only the last 100 notifications in memory
        if (notifications.value.length > 100) {
          notifications.value = notifications.value.slice(0, 100)
        }
      }
    } catch (error) {
      console.error('Error fetching notifications:', error)
    }
  }

  // Fetch unread count
  const fetchUnreadCount = async () => {
    try {
      const data = await $fetch<{ success: boolean; count: number }>(
        '/api/notifications/unread-count'
      )
      
      if (data.success) {
        // Always fetch all notifications to keep in sync, not just unread ones
        await fetchNotifications(50, false)
      }
    } catch (error) {
      console.error('Error fetching unread count:', error)
    }
  }

  // Mark notification as read
  const markAsRead = async (id: string | number) => {
    try {
      await $fetch(`/api/notifications/${id}`, {
        method: 'PUT',
        body: { read: true }
      })
      
      const notification = notifications.value.find(n => n.id === id)
      if (notification) {
        notification.read = true
      }
      
      // Mark as displayed so it won't show as a toast again
      displayedNotificationIds.value.add(String(id))
    } catch (error) {
      console.error('Error marking notification as read:', error)
    }
  }

  // Mark all as read
  const markAllAsRead = async () => {
    try {
      await $fetch('/api/notifications/read-all', {
        method: 'POST'
      })
      
      notifications.value.forEach(n => n.read = true)
    } catch (error) {
      console.error('Error marking all notifications as read:', error)
    }
  }

  // Remove notification from UI only (doesn't delete from DB)
  const removeNotification = (id: string | number) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  // Clear all from UI only
  const clearAll = () => {
    notifications.value = []
  }

  // Add a local notification (for UI-only notifications)
  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'created_at' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      created_at: new Date().toISOString(),
      read: false
    }
    notifications.value.unshift(newNotification)
  }

  // Poll for new notifications
  const startPolling = (intervalMs = 30000) => {
    const poll = async () => {
      await fetchUnreadCount()
    }
    
    // Poll immediately
    poll()
    
    // Then poll at intervals
    const interval = setInterval(poll, intervalMs)
    
    return () => clearInterval(interval)
  }

  // Initialize notifications on startup
  const initializeNotifications = async () => {
    await fetchNotifications(50, false)
    
    // Mark all existing notifications as displayed since they've been loaded
    // Only unread notifications will show as toasts
    notifications.value.forEach(n => {
      displayedNotificationIds.value.add(String(n.id))
    })
  }

  return {
    notifications: readonly(notifications),
    unreadCount,
    fetchNotifications,
    fetchUnreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    startPolling,
    initializeNotifications
  }
}