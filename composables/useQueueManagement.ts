export const useQueueManagement = () => {
  const { showToast } = useToast()

  const skipItem = async (mediaId: number, tmdbId: number, mediaType: string, title: string) => {
    try {
      const response = await $fetch('/api/queue/skip-item', {
        method: 'POST',
        body: {
          media_id: mediaId,
          tmdb_id: tmdbId,
          media_type: mediaType
        }
      })

      if (response.success) {
        showToast({
          type: 'success',
          title: 'Item Skipped',
          message: `Successfully skipped ${title} from queue`
        })
        return { success: true, data: response }
      } else {
        throw new Error(response.message || 'Failed to skip item')
      }
    } catch (error: any) {
      console.error('Error skipping queue item:', error)
      showToast({
        type: 'error',
        title: 'Error',
        message: error.data?.message || error.message || 'Failed to skip item from queue'
      })
      return { success: false, error }
    }
  }

  const clearQueue = async (mediaType?: 'movie' | 'tv') => {
    try {
      const response = await $fetch('/api/queue/clear', {
        method: 'POST',
        body: {
          media_type: mediaType
        }
      })

      if (response.success) {
        const typeLabel = mediaType ? (mediaType === 'movie' ? 'movie' : 'TV') : 'all'
        showToast({
          type: 'success',
          title: 'Queue Cleared',
          message: `Successfully cleared ${response.cleared_count} item(s) from ${typeLabel} queue`
        })
        return { success: true, data: response }
      } else {
        throw new Error(response.message || 'Failed to clear queue')
      }
    } catch (error: any) {
      console.error('Error clearing queue:', error)
      showToast({
        type: 'error',
        title: 'Error',
        message: error.data?.message || error.message || 'Failed to clear queue'
      })
      return { success: false, error }
    }
  }

  return {
    skipItem,
    clearQueue
  }
}

