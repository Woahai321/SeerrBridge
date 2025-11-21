<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
    <Card 
      v-for="stat in stats" 
      :key="stat.title"
      class="relative overflow-hidden"
    >
      <div class="flex items-center justify-between">
        <div class="space-y-1">
          <p class="text-sm font-medium text-muted-foreground">{{ stat.title }}</p>
          <p class="text-2xl font-bold text-foreground">{{ stat.value }}</p>
          <div v-if="stat.change" class="flex items-center space-x-1">
            <AppIcon 
              :icon="stat.changeType === 'positive' ? 'lucide:trending-up' : 'lucide:trending-down'" 
              size="12" 
              :class="stat.changeType === 'positive' ? 'text-success' : 'text-destructive'"
            />
            <span class="text-xs" :class="stat.changeType === 'positive' ? 'text-success' : 'text-destructive'">
              {{ stat.change }}
            </span>
          </div>
        </div>
        <div class="p-3 rounded-lg" :class="stat.bgColor">
          <AppIcon :icon="stat.icon" size="24" :class="stat.iconColor" />
        </div>
      </div>
      
      <!-- Subtle gradient overlay -->
      <div class="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-primary/5 pointer-events-none" />
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useDashboardData } from '~/composables/useDashboardData'
import Card from '~/components/ui/Card.vue'

interface StatCard {
  title: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative'
  icon: string
  bgColor: string
  iconColor: string
}

const { logsData, pending, error } = useDashboardData()

const stats = computed<StatCard[]>(() => {
  if (!logsData.value || !logsData.value.statistics) return []
  
  const stats = logsData.value.statistics
  
  return [
    {
      title: 'Total Logs',
      value: stats.totalLogs.toLocaleString(),
      icon: 'lucide:file-text',
      bgColor: 'bg-primary/10',
      iconColor: 'text-primary'
    },
    {
      title: 'Success Rate',
      value: (() => {
        const totalRelevantLogs = stats.successCount + stats.errorCount
        if (totalRelevantLogs === 0) return 'N/A'
        return `${Math.round((stats.successCount / totalRelevantLogs) * 100)}%`
      })(),
      change: `+${stats.successCount} today`,
      changeType: 'positive',
      icon: 'lucide:check-circle',
      bgColor: 'bg-success/10',
      iconColor: 'text-success'
    },
    {
      title: 'Errors',
      value: stats.errorCount,
      change: stats.criticalErrors > 0 ? `${stats.criticalErrors} critical` : undefined,
      changeType: stats.criticalErrors > 0 ? 'negative' : undefined,
      icon: 'lucide:alert-circle',
      bgColor: 'bg-destructive/10',
      iconColor: 'text-destructive'
    },
    {
      title: 'Successful Grabs',
      value: stats.successfulGrabs,
      change: (() => {
        const recentCount = stats.recentCompletedMedia?.length || 0
        if (recentCount === 0) return undefined
        
        // Calculate total recent completed items (movies + seasons)
        const totalRecentCompleted = stats.recentCompletedMedia?.reduce((sum: number, item: any) => {
          return sum + (item.completed_count || 1)
        }, 0) || 0
        
        return `+${totalRecentCompleted} recent`
      })(),
      changeType: 'positive',
      icon: 'lucide:download',
      bgColor: 'bg-info/10',
      iconColor: 'text-info'
    }
  ]
})
</script>
