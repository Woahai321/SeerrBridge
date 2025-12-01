<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    @click.self="handleClose"
  >
    <div class="glass-card-enhanced rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-foreground">Add New List</h2>
        <button
          @click="handleClose"
          class="p-2 hover:bg-muted rounded-lg transition-colors"
        >
          <AppIcon icon="lucide:x" size="20" class="text-foreground" />
        </button>
      </div>

      <!-- Progress Indicator -->
      <div class="flex items-center justify-center gap-2 mb-6">
        <div
          v-for="step in 2"
          :key="step"
          :class="[
            'h-1.5 rounded-full transition-all',
            step === currentStep ? 'w-8 bg-primary' : step < currentStep ? 'w-6 bg-primary/50' : 'w-6 bg-muted'
          ]"
        />
      </div>

      <!-- Step 1: Choose Provider -->
      <div v-if="currentStep === 1" class="space-y-4">
        <div class="text-center space-y-1.5 mb-6">
          <p class="text-sm text-muted-foreground font-medium">
            Select a source for your list
          </p>
          <p class="text-xs text-muted-foreground">
            Choose one provider to add a list from
          </p>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <!-- Trakt -->
          <button
            @click="selectSource('trakt')"
            :class="[
              'p-4 rounded-xl border-2 transition-all duration-300',
              selectedSource === 'trakt'
                ? 'border-primary bg-primary/20'
                : 'border-border bg-card hover:border-primary/50 hover:bg-muted/30'
            ]"
          >
            <div class="flex flex-col items-center gap-3">
              <div :class="[
                'p-3 rounded-xl transition-all duration-300',
                selectedSource === 'trakt' ? 'bg-primary/30 border border-primary/40' : 'bg-green-500/20 border border-transparent'
              ]">
                <AppIcon icon="lucide:trending-up" size="28" :class="selectedSource === 'trakt' ? 'text-primary' : 'text-green-400'" />
              </div>
              <div class="text-center">
                <span class="font-semibold text-foreground block">Trakt</span>
                <span class="text-xs text-muted-foreground mt-1">Track your movies & TV</span>
              </div>
            </div>
          </button>

          <!-- Trakt Special -->
          <button
            @click="selectSource('trakt_special')"
            :class="[
              'p-4 rounded-xl border-2 transition-all duration-300',
              selectedSource === 'trakt_special'
                ? 'border-primary bg-primary/20'
                : 'border-border bg-card hover:border-primary/50 hover:bg-muted/30'
            ]"
          >
            <div class="flex flex-col items-center gap-3">
              <div :class="[
                'p-3 rounded-xl transition-all duration-300',
                selectedSource === 'trakt_special' ? 'bg-primary/30 border border-primary/40' : 'bg-purple-500/20 border border-transparent'
              ]">
                <AppIcon icon="lucide:zap" size="28" :class="selectedSource === 'trakt_special' ? 'text-primary' : 'text-purple-400'" />
              </div>
              <div class="text-center">
                <span class="font-semibold text-foreground block">Trakt Special</span>
                <span class="text-xs text-muted-foreground mt-1">Curated Trakt lists</span>
              </div>
            </div>
          </button>

          <!-- IMDb - Coming Soon -->
          <button
            disabled
            class="p-4 rounded-xl border-2 border-border bg-card/50 opacity-60 cursor-not-allowed relative"
          >
            <div class="flex flex-col items-center gap-3">
              <div class="p-3 rounded-xl bg-yellow-500/20 border border-transparent">
                <AppIcon icon="lucide:star" size="28" class="text-yellow-400" />
              </div>
              <div class="text-center">
                <span class="font-semibold text-foreground block">IMDb</span>
                <span class="text-xs text-muted-foreground mt-1">Coming Soon</span>
              </div>
            </div>
            <div class="absolute top-2 right-2">
              <span class="px-2 py-0.5 text-xs rounded-full bg-muted text-muted-foreground">Soon</span>
            </div>
          </button>

          <!-- Letterboxd -->
          <button
            @click="selectSource('letterboxd')"
            :class="[
              'p-4 rounded-xl border-2 transition-all duration-300',
              selectedSource === 'letterboxd'
                ? 'border-primary bg-primary/20'
                : 'border-border bg-card hover:border-primary/50 hover:bg-muted/30'
            ]"
          >
            <div class="flex flex-col items-center gap-3">
              <div :class="[
                'p-3 rounded-xl transition-all duration-300',
                selectedSource === 'letterboxd' ? 'bg-primary/30 border border-primary/40' : 'bg-pink-500/20 border border-transparent'
              ]">
                <AppIcon icon="lucide:book-open" size="28" :class="selectedSource === 'letterboxd' ? 'text-primary' : 'text-pink-400'" />
              </div>
              <div class="text-center">
                <span class="font-semibold text-foreground block">Letterboxd</span>
                <span class="text-xs text-muted-foreground mt-1">Movie lists & watchlists</span>
              </div>
            </div>
          </button>

          <!-- MDBList - Coming Soon -->
          <button
            disabled
            class="p-4 rounded-xl border-2 border-border bg-card/50 opacity-60 cursor-not-allowed relative"
          >
            <div class="flex flex-col items-center gap-3">
              <div class="p-3 rounded-xl bg-blue-500/20 border border-transparent">
                <AppIcon icon="lucide:database" size="28" class="text-blue-400" />
              </div>
              <div class="text-center">
                <span class="font-semibold text-foreground block">MDBList</span>
                <span class="text-xs text-muted-foreground mt-1">Coming Soon</span>
              </div>
            </div>
            <div class="absolute top-2 right-2">
              <span class="px-2 py-0.5 text-xs rounded-full bg-muted text-muted-foreground">Soon</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Step 2: Enter List Details -->
      <div v-else-if="currentStep === 2" class="space-y-4">
          <div class="flex items-center justify-between mb-4">
            <button
              type="button"
              class="p-1 rounded hover:bg-muted transition-colors"
              @click="currentStep = 1"
            >
              <AppIcon icon="lucide:chevron-left" size="20" />
            </button>
            <div class="flex items-center gap-2">
              <AppIcon 
                :icon="getSourceIcon(selectedSource)" 
                size="16" 
                class="text-primary" 
              />
              <span class="text-sm font-medium text-foreground">
                {{ getSourceLabel(selectedSource) }}
              </span>
            </div>
          </div>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- Trakt Special Lists -->
          <div v-if="selectedSource === 'trakt_special'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-foreground mb-3">
                Choose List Type
              </label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="type in traktSpecialTypes"
                  :key="type.value"
                  type="button"
                  :class="[
                    'p-3 rounded-lg border-2 text-sm font-medium transition-all',
                    selectedTraktType === type.value
                      ? 'border-primary bg-primary/20 text-primary'
                      : 'border-border bg-card text-foreground hover:border-primary/50'
                  ]"
                  @click="selectedTraktType = type.value"
                >
                  {{ type.label }}
                </button>
              </div>
            </div>

            <div v-if="selectedTraktType">
              <label class="block text-sm font-medium text-foreground mb-3">
                Choose Media Type
              </label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="media in traktMediaTypes"
                  :key="media.value"
                  type="button"
                  :class="[
                    'p-3 rounded-lg border-2 text-sm font-medium transition-all',
                    selectedTraktMedia === media.value
                      ? 'border-success bg-success/20 text-success'
                      : 'border-border bg-card text-foreground hover:border-success/50'
                  ]"
                  @click="selectedTraktMedia = media.value"
                >
                  {{ media.label }}
                </button>
              </div>
            </div>
          </div>

          <!-- Regular Trakt List URL -->
          <div v-else-if="selectedSource === 'trakt'">
            <label class="block text-sm font-medium text-foreground mb-2">
              Trakt List URL or ID
            </label>
            <input
              v-model="listId"
              type="text"
              placeholder="https://app.trakt.tv/users/username/lists/list-name or list ID"
              class="w-full px-4 py-2 bg-card border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors"
              :class="{ 'border-destructive': error }"
            />
            <p v-if="error" class="text-xs text-destructive mt-1">{{ error }}</p>
            <p class="text-xs text-muted-foreground mt-2">
              Enter a Trakt list URL or identifier. You can also use special lists like "trending:movies" or "popular:shows"
            </p>
          </div>

          <!-- Letterboxd List URL -->
          <div v-else-if="selectedSource === 'letterboxd'">
            <label class="block text-sm font-medium text-foreground mb-2">
              Letterboxd List URL or ID
            </label>
            <input
              v-model="listId"
              type="text"
              placeholder="https://letterboxd.com/username/list/list-name/ or username/list-slug"
              class="w-full px-4 py-2 bg-card border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors"
              :class="{ 'border-destructive': error }"
            />
            <p v-if="error" class="text-xs text-destructive mt-1">{{ error }}</p>
            <p class="text-xs text-muted-foreground mt-2">
              Enter a Letterboxd list URL or identifier. Supports custom lists and watchlists. Note: This uses web scraping and may take longer.
            </p>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-end gap-3 pt-4">
            <button
              type="button"
              @click="handleClose"
              class="px-4 py-2 text-foreground hover:bg-muted rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="loading || !canSubmit"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg transition-colors hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <AppIcon
                v-if="loading"
                icon="lucide:loader-2"
                size="16"
                class="animate-spin"
              />
              <span>Add & Sync</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'list-added': [data: { listId: string; sync: boolean }]
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

// State
const currentStep = ref(1)
const selectedSource = ref('')
const listId = ref('')
const error = ref('')
const loading = ref(false)
const showTraktSpecial = ref(false)
const selectedTraktType = ref('')
const selectedTraktMedia = ref('')

// Trakt special list options
const traktSpecialTypes = [
  { label: 'Trending', value: 'trending' },
  { label: 'Popular', value: 'popular' },
  { label: 'Anticipated', value: 'anticipated' },
  { label: 'Box Office', value: 'boxoffice' },
]

const traktMediaTypes = [
  { label: 'Movies', value: 'movies' },
  { label: 'TV Shows', value: 'shows' },
]

const canSubmit = computed(() => {
  if (selectedSource.value === 'trakt_special') {
    return selectedTraktType.value && selectedTraktMedia.value
  }
  if (selectedSource.value === 'letterboxd' || selectedSource.value === 'trakt') {
    return listId.value.trim().length > 0
  }
  return false
})

const selectSource = (source: string) => {
  if (source === 'trakt' || source === 'trakt_special' || source === 'letterboxd') {
    selectedSource.value = source
    showTraktSpecial.value = source === 'trakt_special'
    currentStep.value = 2
  }
}

const getSourceIcon = (source: string) => {
  const icons: Record<string, string> = {
    trakt: 'lucide:trending-up',
    trakt_special: 'lucide:zap',
    letterboxd: 'lucide:book-open'
  }
  return icons[source] || 'lucide:list'
}

const getSourceLabel = (source: string) => {
  const labels: Record<string, string> = {
    trakt: 'Trakt',
    trakt_special: 'Trakt Special',
    letterboxd: 'Letterboxd'
  }
  return labels[source] || 'List'
}

const handleClose = () => {
  // Reset form
  currentStep.value = 1
  selectedSource.value = ''
  listId.value = ''
  error.value = ''
  showTraktSpecial.value = false
  selectedTraktType.value = ''
  selectedTraktMedia.value = ''
  isOpen.value = false
}

const handleSubmit = async () => {
  if (!canSubmit.value) return

  loading.value = true
  error.value = ''

  try {
    let finalListId = listId.value.trim()
    
    // If using Trakt special, construct the ID
    if (selectedSource.value === 'trakt_special' && selectedTraktType.value && selectedTraktMedia.value) {
      finalListId = `${selectedTraktType.value}:${selectedTraktMedia.value}`
    }

    if (!finalListId) {
      error.value = selectedSource.value === 'trakt_special' 
        ? 'Please select list type and media type'
        : 'Please enter a list URL or ID'
      loading.value = false
      return
    }

    // Always sync immediately
    emit('list-added', { listId: finalListId, sync: true })

    handleClose()
  } catch (err: any) {
    error.value = err.message || 'Failed to add list'
  } finally {
    loading.value = false
  }
}
</script>

