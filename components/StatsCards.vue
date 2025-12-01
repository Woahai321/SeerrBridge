<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
    <Card 
      v-for="(stat, index) in stats" 
      :key="stat.title"
      class="relative overflow-hidden group hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
      :style="{ animationDelay: `${index * 100}ms` }"
    >
      <!-- Animated gradient border on hover -->
      <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-primary/0 via-primary/0 to-accent/0 group-hover:from-primary/10 group-hover:via-primary/5 group-hover:to-accent/10 transition-all duration-500 pointer-events-none" />
      
      <!-- Top accent bar -->
      <div 
        class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r transition-all duration-500"
        :class="stat.gradientColors"
      />
      
      <div class="flex items-center justify-between relative z-10">
        <div class="space-y-1 sm:space-y-1.5 flex-1 min-w-0">
          <p class="text-xs sm:text-sm font-medium text-muted-foreground truncate">{{ stat.title }}</p>
          <div class="flex items-baseline space-x-2">
            <p 
              class="text-2xl sm:text-3xl font-bold text-foreground tabular-nums"
              :key="`value-${stat.value}`"
            >
              <AnimatedNumber :value="stat.numericValue" :duration="1000" />
            </p>
            <span v-if="stat.suffix" class="text-base sm:text-lg text-muted-foreground">{{ stat.suffix }}</span>
          </div>
          <div v-if="stat.change" class="flex items-center space-x-1.5 mt-1">
            <AppIcon 
              :icon="stat.changeType === 'positive' ? 'lucide:trending-up' : 'lucide:trending-down'" 
              size="14" 
              :class="stat.changeType === 'positive' ? 'text-success' : 'text-destructive'"
            />
            <span 
              class="text-xs font-medium truncate" 
              :class="stat.changeType === 'positive' ? 'text-success' : 'text-destructive'"
            >
              {{ stat.change }}
            </span>
          </div>
        </div>
        <div 
          class="w-10 h-10 sm:w-12 sm:h-12 rounded-lg sm:rounded-xl flex items-center justify-center group-hover:scale-110 group-hover:rotate-3 transition-all duration-300 flex-shrink-0"
          :class="stat.bgColor"
        >
          <AppIcon 
            :icon="stat.icon" 
            size="20" 
            class="sm:w-6 sm:h-6 transition-transform duration-300 group-hover:scale-110"
            :class="stat.iconColor"
          />
        </div>
      </div>
      
      <!-- Subtle shimmer effect -->
      <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 pointer-events-none" />
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useDashboardData } from '~/composables/useDashboardData'
import { useProcessingStatus } from '~/composables/useProcessingStatus'
import Card from '~/components/ui/Card.vue'
import AnimatedNumber from '~/components/AnimatedNumber.vue'

interface StatCard {
  title: string
  value: string | number
  numericValue: number
  suffix?: string
  change?: string
  changeType?: 'positive' | 'negative'
  icon: string
  bgColor: string
  iconColor: string
  gradientColors: string
}

const { logsData, pending, error } = useDashboardData()

// Get processing status - handle errors gracefully
const processingStatusResult = useProcessingStatus()
const processingData = processingStatusResult?.processingData || ref({
  stats: {
    total_processing: 0,
    movies_processing: 0,
    tv_processing: 0
  }
})

// Fetch media stats with error handling
const { data: mediaStats } = await useLazyAsyncData('media-stats', async () => {
  try {
    const response = await $fetch('/api/unified-media?limit=1')
    if (response.success && response.data) {
      return response.data.stats
    }
  } catch (err) {
    console.error('Error fetching media stats:', err)
  }
  return {
    total_media: 0,
    total_movies: 0,
    total_tv_shows: 0,
    completed_count: 0,
    processing_count: 0,
    failed_count: 0,
    movies_completed: 0,
    tv_completed: 0,
    movies_failed: 0,
    tv_failed: 0,
    movies_processing: 0,
    tv_processing: 0
  }
}, {
  server: false,
  default: () => ({
    total_media: 0,
    total_movies: 0,
    total_tv_shows: 0,
    completed_count: 0,
    processing_count: 0,
    failed_count: 0,
    movies_completed: 0,
    tv_completed: 0,
    movies_failed: 0,
    tv_failed: 0,
    movies_processing: 0,
    tv_processing: 0
  })
})

const stats = computed<StatCard[]>(() => {
  const statsData = logsData.value?.statistics
  const media = mediaStats.value || {}
  const processing = processingData.value?.stats || { total_processing: 0, movies_processing: 0, tv_processing: 0 }
  
  return [
    {
      title: 'Total Processed',
      value: media.total_media || 0,
      numericValue: media.total_media || 0,
      change: `${media.total_movies || 0} movies, ${media.total_tv_shows || 0} TV`,
      changeType: 'positive',
      icon: 'lucide:film',
      bgColor: 'bg-primary/10',
      iconColor: 'text-primary',
      gradientColors: 'from-primary via-primary/80 to-accent'
    },
    {
      title: 'Successfully Completed',
      value: media.completed_count || 0,
      numericValue: media.completed_count || 0,
      change: `${media.movies_completed || 0} movies, ${media.tv_completed || 0} TV`,
      changeType: 'positive',
      icon: 'lucide:check-circle-2',
      bgColor: 'bg-success/10',
      iconColor: 'text-success',
      gradientColors: 'from-success via-emerald-500 to-green-500'
    },
    {
      title: 'Currently Processing',
      value: processing.total_processing || media.processing_count || 0,
      numericValue: processing.total_processing || media.processing_count || 0,
      change: `${processing.movies_processing || 0} movies, ${processing.tv_processing || 0} TV`,
      changeType: 'positive',
      icon: 'lucide:loader-2',
      bgColor: 'bg-info/10',
      iconColor: 'text-info',
      gradientColors: 'from-info via-blue-500 to-cyan-500'
    },
    {
      title: 'Failed Items',
      value: media.failed_count || 0,
      numericValue: media.failed_count || 0,
      change: `${media.movies_failed || 0} movies, ${media.tv_failed || 0} TV`,
      changeType: media.failed_count > 0 ? 'negative' : undefined,
      icon: 'lucide:alert-circle',
      bgColor: 'bg-destructive/10',
      iconColor: 'text-destructive',
      gradientColors: 'from-destructive via-red-500 to-rose-500'
    }
  ]
})
</script>
