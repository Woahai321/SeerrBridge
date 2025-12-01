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
  const pageLoadTime = ref<Date>(new Date()) // Track when page loaded to only show new notifications

  // Track if we're currently fetching to prevent concurrent fetches
  let isFetching = false
  
  // Fetch notifications from backend
  const fetchNotifications = async (limit = 50, unreadOnly = false) => {
    // Prevent concurrent fetches
    if (isFetching) {
      return
    }
    
    isFetching = true
    try {
      const query = new URLSearchParams({
        limit: limit.toString(),
        unreadOnly: unreadOnly.toString()
      })
      
      const data = await $fetch<{ success: boolean; data: Notification[] }>(
        `/api/notifications?${query}`
      )
      
      if (data.success && data.data) {
        // Get existing notification IDs (both in list and displayed)
        const existingIds = new Set(notifications.value.map(n => String(n.id)))
        
        // Filter out duplicates and only get truly new notifications
        const newNotifications = data.data.filter(n => {
          const notificationId = String(n.id)
          
          // Don't show toasts for read notifications
          if (n.read) {
            return false
          }
          
          // Check if already displayed (this is the key check to prevent duplicates)
          if (displayedNotificationIds.value.has(notificationId)) {
            return false
          }
          
          // Check if already in local list
          if (existingIds.has(notificationId)) {
            return false
          }
          
          // Only show toasts for notifications created AFTER page load
          // This prevents old notifications from showing as toasts on refresh
          if (pageLoadTime.value) {
            const notificationTime = new Date(n.created_at || n.timestamp)
            const pageLoad = new Date(pageLoadTime.value)
            // Add 1 second buffer to account for timing differences
            if (notificationTime.getTime() < (pageLoad.getTime() - 1000)) {
              // Mark as displayed so we don't check it again, but don't show as toast
              displayedNotificationIds.value.add(notificationId)
              return false
            }
          }
          
          return true
        })
        
        // Update existing notifications if they exist (for read status updates)
        data.data.forEach(backendNotif => {
          const existingIndex = notifications.value.findIndex(n => String(n.id) === String(backendNotif.id))
          if (existingIndex !== -1) {
            // Update read status
            notifications.value[existingIndex].read = backendNotif.read
          } else {
            // If notification exists in backend but not in our list, add it (but mark as displayed if read)
            // This handles the case where notifications were cleared from UI but still exist in DB
            if (backendNotif.read) {
              // Don't add read notifications that we haven't seen before
              displayedNotificationIds.value.add(String(backendNotif.id))
            }
          }
        })
        
        // Add new notifications to the beginning
        if (newNotifications.length > 0) {
          // IMPORTANT: Mark as displayed BEFORE adding to prevent race conditions
          // This ensures that if another poll happens while we're processing, it won't add duplicates
          newNotifications.forEach(n => {
            displayedNotificationIds.value.add(String(n.id))
          })
          
          // Filter out any that might have been added between the check and now (extra safety)
          const trulyNew = newNotifications.filter(n => {
            const id = String(n.id)
            return !notifications.value.some(existing => String(existing.id) === id)
          })
          
          // Now add to list
          if (trulyNew.length > 0) {
            notifications.value.unshift(...trulyNew)
          }
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
    } finally {
      isFetching = false
    }
  }

  // Fetch unread count
  const fetchUnreadCount = async () => {
    try {
      const data = await $fetch<{ success: boolean; count: number }>(
        '/api/notifications/unread-count'
      )
      
      if (data.success && data.count > 0) {
        // Only fetch if there are unread notifications to avoid unnecessary calls
        // Fetch only unread notifications to reduce duplicates
        await fetchNotifications(50, true)
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

  // Ultra real-time polling for notifications
  let pollingInterval: ReturnType<typeof setInterval> | null = null
  
  const startPolling = (intervalMs = 1000) => {
    const poll = async () => {
      // Only poll if pageLoadTime is set (initialization complete)
      if (pageLoadTime.value) {
        await fetchUnreadCount()
      }
    }
    
    // Don't poll immediately - wait for initialization to complete
    // The first poll will happen after the interval
    
    // Then poll at intervals (ultra aggressive for real-time)
    pollingInterval = setInterval(poll, intervalMs)
    
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
        pollingInterval = null
      }
    }
  }

  // Initialize notifications on startup
  const initializeNotifications = async () => {
    // Set page load time to NOW - only notifications created after this will show as toasts
    // This prevents old notifications from showing as toasts on page refresh
    pageLoadTime.value = new Date()
    
    // Fetch existing notifications (but they won't show as toasts if created before pageLoadTime)
    await fetchNotifications(50, false)
    
    // Mark ALL fetched notifications as displayed (even if they're old)
    // This ensures they won't show as toasts, but they'll still be in the notification history
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