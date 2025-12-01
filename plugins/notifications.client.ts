export default defineNuxtPlugin(() => {
  // Request notification permission on client side
  if (process.client && 'Notification' in window) {
    if (Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }
})
