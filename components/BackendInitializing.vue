<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
    <div class="glass-card-enhanced rounded-2xl p-8 md:p-12 max-w-md w-full mx-4 animate-fade-in-up">
      <div class="flex flex-col items-center space-y-6">
        <!-- Animated Logo/Icon -->
        <div class="relative">
          <div class="w-20 h-20 rounded-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center animate-pulse-soft">
            <Icon name="lucide:server" class="w-10 h-10 text-primary animate-spin" />
          </div>
          <!-- Pulsing ring effect -->
          <div class="absolute inset-0 rounded-full border-2 border-primary/30 animate-ping"></div>
        </div>

        <!-- Title -->
        <div class="text-center space-y-2">
          <h2 class="text-2xl md:text-3xl font-bold text-foreground">
            Getting Everything Ready
          </h2>
          <p class="text-sm md:text-base text-muted-foreground">
            Initializing SeerrBridge backend...
          </p>
        </div>

        <!-- Status Messages -->
        <div class="w-full space-y-3">
          <div 
            v-for="(status, index) in statusMessages" 
            :key="index"
            class="flex items-center space-x-3 text-sm"
            :class="status.completed ? 'text-muted-foreground' : 'text-foreground'"
          >
            <Icon 
              :name="status.completed ? 'lucide:check-circle' : status.active ? 'lucide:loader-2' : 'lucide:circle'" 
              class="w-5 h-5 flex-shrink-0"
              :class="[
                status.completed ? 'text-green-500' : 
                status.active ? 'text-primary animate-spin' : 
                'text-muted-foreground'
              ]"
            />
            <span :class="status.completed ? 'line-through opacity-60' : ''">
              {{ status.message }}
            </span>
          </div>
        </div>

        <!-- Progress Indicator -->
        <div class="w-full space-y-2">
          <div class="h-2 bg-muted rounded-full overflow-hidden">
            <div 
              class="h-full bg-gradient-to-r from-primary to-primary/60 rounded-full transition-all duration-500 ease-out"
              :style="{ width: `${progress}%` }"
            ></div>
          </div>
          <p class="text-xs text-center text-muted-foreground">
            {{ currentStatusMessage }}
          </p>
        </div>

        <!-- Animated dots -->
        <div class="flex items-center space-x-1">
          <div 
            v-for="i in 3" 
            :key="i"
            class="w-2 h-2 rounded-full bg-primary animate-pulse"
            :style="{ animationDelay: `${(i - 1) * 0.2}s` }"
          ></div>
        </div>

        <!-- Close/Skip Button -->
        <button
          @click="handleClose"
          class="mt-4 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors duration-200 border border-border rounded-lg hover:border-primary/50 hover:bg-primary/5"
        >
          Skip and continue
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useBridgeStatus } from '~/composables/useBridgeStatus'

const emit = defineEmits(['ready'])

const { fetchStatus } = useBridgeStatus()

const statusMessages = ref([
  { message: 'Checking and fixing directory permissions...', completed: false, active: false },
  { message: 'Starting backend with uvicorn...', completed: false, active: false },
  { message: 'Waiting for application startup...', completed: false, active: false },
  { message: 'Backend ready!', completed: false, active: false }
])

const progress = ref(0)
const currentStatusMessage = ref('Initializing...')
const checkInterval = ref(null)
const statusIndex = ref(0)

const updateStatus = (index, active = false, completed = false) => {
  if (index >= 0 && index < statusMessages.value.length) {
    statusMessages.value[index].active = active
    statusMessages.value[index].completed = completed
  }
}

const checkBackendStatus = async () => {
  try {
    const status = await fetchStatus()
    
    // Check if backend is running and status is recent (within last 30 seconds)
    // The service-status endpoint returns 'offline' if status is stale or not found
    if (status && status.status === 'running' && status.uptime_seconds !== undefined && status.uptime_seconds > 0) {
      // Backend is ready!
      updateStatus(3, false, true)
      progress.value = 100
      currentStatusMessage.value = 'Backend is ready!'
      
      // Clear interval and emit ready event
      if (checkInterval.value) {
        clearInterval(checkInterval.value)
        checkInterval.value = null
      }
      
      // Wait a moment for visual feedback, then redirect
      setTimeout(() => {
        emit('ready')
      }, 1000)
      return
    }
    
    // Backend not ready yet - update progress
    updateProgress()
    
  } catch (error) {
    // Continue checking even if there's an error (backend might not be ready yet)
    // This is expected during initialization
    updateProgress()
  }
}

const updateProgress = () => {
  // Simulate progress through status messages based on elapsed time
  const elapsed = Date.now() - startTime.value
  const progressPercent = Math.min(95, (elapsed / 60000) * 100) // Max 95% until ready
  progress.value = progressPercent
  
  // Update status messages based on elapsed time
  if (elapsed > 5000 && statusIndex.value === 0) {
    updateStatus(0, false, true)
    updateStatus(1, true, false)
    statusIndex.value = 1
    currentStatusMessage.value = 'Starting backend service...'
  } else if (elapsed > 15000 && statusIndex.value === 1) {
    updateStatus(1, false, true)
    updateStatus(2, true, false)
    statusIndex.value = 2
    currentStatusMessage.value = 'Waiting for application startup...'
  } else if (elapsed > 30000 && statusIndex.value === 2) {
    updateStatus(2, false, true)
    updateStatus(3, true, false)
    statusIndex.value = 3
    currentStatusMessage.value = 'Finalizing startup...'
  }
}

const startTime = ref(Date.now())

const handleClose = () => {
  // Clear the interval if it's still running
  if (checkInterval.value) {
    clearInterval(checkInterval.value)
    checkInterval.value = null
  }
  // Emit ready event to close the overlay
  emit('ready')
}

onMounted(() => {
  // Start with first status active
  updateStatus(0, true, false)
  currentStatusMessage.value = 'Checking and fixing directory permissions...'
  
  // Start checking backend status every 2 seconds
  checkBackendStatus() // Initial check
  checkInterval.value = setInterval(checkBackendStatus, 2000)
  
  // Safety timeout - if backend doesn't start in 2 minutes, proceed anyway
  setTimeout(() => {
    if (checkInterval.value) {
      console.warn('Backend initialization timeout - proceeding anyway')
      clearInterval(checkInterval.value)
      checkInterval.value = null
      emit('ready')
    }
  }, 120000) // 2 minutes
})

onUnmounted(() => {
  if (checkInterval.value) {
    clearInterval(checkInterval.value)
    checkInterval.value = null
  }
})
</script>

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
}
</style>

