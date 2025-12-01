<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <!-- Background overlay -->
      <div class="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" @click="$emit('close')"></div>

      <!-- Modal panel -->
      <div class="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
        <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              Failed Items Configuration
            </h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              <AppIcon icon="lucide:x" size="20" />
            </button>
          </div>

          <div v-if="loading" class="flex items-center justify-center py-8">
            <AppIcon icon="lucide:loader-2" size="32" class="animate-spin text-primary" />
          </div>

          <div v-else class="space-y-6">
            <!-- Configuration Settings -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Left Column -->
              <div class="space-y-4">
                <h4 class="text-md font-medium text-gray-900 dark:text-white">Retry Settings</h4>
                
                <!-- Enable Failed Item Retry -->
                <div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div>
                    <label class="text-sm font-medium text-gray-900 dark:text-white">Enable Failed Item Retry</label>
                    <p class="text-xs text-gray-500 dark:text-gray-400">Enable or disable the automatic retry of failed media items</p>
                  </div>
                  <div class="flex items-center space-x-2">
                    <input
                      v-model="config.enable_failed_item_retry"
                      type="checkbox"
                      class="w-4 h-4 text-primary bg-background border-border rounded focus:ring-primary"
                    />
                  </div>
                </div>

                <!-- Retry Interval -->
                <div>
                  <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Retry Interval (minutes)
                  </label>
                  <input
                    v-model.number="config.failed_item_retry_interval_minutes"
                    type="number"
                    min="1"
                    max="1440"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Interval between failed item retry checks</p>
                </div>

                <!-- Max Retry Attempts -->
                <div>
                  <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Max Retry Attempts
                  </label>
                  <input
                    v-model.number="config.failed_item_max_retry_attempts"
                    type="number"
                    min="1"
                    max="10"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Maximum number of retry attempts for failed items</p>
                </div>
              </div>

              <!-- Right Column -->
              <div class="space-y-4">
                <h4 class="text-md font-medium text-gray-900 dark:text-white">Timing Settings</h4>
                
                <!-- Initial Retry Delay -->
                <div>
                  <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Initial Retry Delay (hours)
                  </label>
                  <input
                    v-model.number="config.failed_item_retry_delay_hours"
                    type="number"
                    min="1"
                    max="168"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Initial delay before first retry attempt</p>
                </div>

                <!-- Backoff Multiplier -->
                <div>
                  <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Backoff Multiplier
                  </label>
                  <input
                    v-model.number="config.failed_item_retry_backoff_multiplier"
                    type="number"
                    min="1"
                    max="10"
                    step="0.1"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Multiplier for exponential backoff (e.g., 2 = 2h, 4h, 8h)</p>
                </div>

                <!-- Max Retry Delay -->
                <div>
                  <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                    Max Retry Delay (hours)
                  </label>
                  <input
                    v-model.number="config.failed_item_max_retry_delay_hours"
                    type="number"
                    min="1"
                    max="168"
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Maximum delay between retry attempts</p>
                </div>
              </div>
            </div>

            <!-- Current Statistics -->
            <div class="border-t border-gray-200 dark:border-gray-700 pt-6">
              <h4 class="text-md font-medium text-gray-900 dark:text-white mb-4">Current Statistics</h4>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.total_failed || 0 }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">Total Failed</div>
                </div>
                <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.failed_movies || 0 }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">Failed Movies</div>
                </div>
                <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.failed_tv_shows || 0 }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">Failed TV Shows</div>
                </div>
                <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div class="text-2xl font-bold text-gray-900 dark:text-white">{{ stats.queued_for_retry || 0 }}</div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">Queued for Retry</div>
                </div>
              </div>
            </div>

            <!-- Retry Schedule -->
            <div v-if="retrySchedule.length > 0" class="border-t border-gray-200 dark:border-gray-700 pt-6">
              <h4 class="text-md font-medium text-gray-900 dark:text-white mb-4">Retry Schedule</h4>
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead class="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Retry Attempt
                      </th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Count
                      </th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Oldest Error
                      </th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Newest Error
                      </th>
                    </tr>
                  </thead>
                  <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    <tr v-for="schedule in retrySchedule" :key="schedule.retry_attempt">
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {{ schedule.retry_attempt }}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {{ schedule.count }}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {{ formatDate(schedule.oldest_error) }}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {{ formatDate(schedule.newest_error) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <Button
            @click="saveConfig"
            :disabled="saving"
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-primary text-white text-base font-medium hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary sm:ml-3 sm:w-auto sm:text-sm"
          >
            <AppIcon v-if="saving" icon="lucide:loader-2" size="16" class="animate-spin mr-2" />
            <AppIcon v-else icon="lucide:save" size="16" class="mr-2" />
            {{ saving ? 'Saving...' : 'Save Configuration' }}
          </Button>
          <Button
            @click="$emit('close')"
            variant="outline"
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '~/composables/useToast'

const emit = defineEmits(['close', 'saved'])
const toast = useToast()

// Reactive data
const loading = ref(false)
const saving = ref(false)
const config = reactive({
  enable_failed_item_retry: true,
  failed_item_retry_interval_minutes: 30,
  failed_item_max_retry_attempts: 3,
  failed_item_retry_delay_hours: 2,
  failed_item_retry_backoff_multiplier: 2,
  failed_item_max_retry_delay_hours: 24
})
const stats = ref({})
const retrySchedule = ref([])

// Methods
const fetchConfig = async () => {
  loading.value = true
  try {
    const response = await $fetch('/api/failed-items-config')
    Object.assign(config, response.config)
    stats.value = response.stats
    retrySchedule.value = response.retry_schedule
  } catch (error) {
    console.error('Error fetching failed items config:', error)
    toast.error('Failed to load configuration')
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const response = await $fetch('/api/failed-items-config', {
      method: 'PUT',
      body: config
    })
    
    toast.success('Configuration saved successfully')
    emit('saved')
  } catch (error) {
    console.error('Error saving failed items config:', error)
    toast.error('Failed to save configuration')
  } finally {
    saving.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleString()
}

// Lifecycle
onMounted(() => {
  fetchConfig()
})
</script>
