import { useNotifications } from './useNotifications'

export const useToast = () => {
  const { addNotification } = useNotifications()

  const toast = {
    success: (message: string, title?: string) => {
      addNotification({
        type: 'success',
        title: title || 'Success',
        message
      })
    },
    
    error: (message: string, title?: string) => {
      addNotification({
        type: 'error',
        title: title || 'Error',
        message
      })
    },
    
    warning: (message: string, title?: string) => {
      addNotification({
        type: 'warning',
        title: title || 'Warning',
        message
      })
    },
    
    info: (message: string, title?: string) => {
      addNotification({
        type: 'info',
        title: title || 'Info',
        message
      })
    }
  }

  return { toast }
}
