<template>
  <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-4">
    <div class="text-center p-3 sm:p-4 bg-muted/20 border border-border rounded-lg">
      <div class="text-2xl sm:text-3xl font-bold text-foreground">{{ stats.total || stats.totalItems || 0 }}</div>
      <div class="text-xs sm:text-sm text-muted-foreground mt-1">Total</div>
    </div>
    <div class="text-center p-3 sm:p-4 bg-success/10 border border-success/30 rounded-lg">
      <div class="text-2xl sm:text-3xl font-bold text-success">{{ stats.requested || stats.itemsRequested || 0 }}</div>
      <div class="text-xs sm:text-sm text-muted-foreground mt-1">Requested</div>
    </div>
    <div class="text-center p-3 sm:p-4 bg-info/10 border border-info/30 rounded-lg">
      <div class="text-2xl sm:text-3xl font-bold text-info">{{ stats.alreadyRequested || stats.itemsAlreadyRequested || 0 }}</div>
      <div class="text-xs sm:text-sm text-muted-foreground mt-1">Already Req</div>
    </div>
    <div class="text-center p-3 sm:p-4 bg-primary/10 border border-primary/30 rounded-lg">
      <div class="text-2xl sm:text-3xl font-bold text-primary">{{ stats.alreadyAvailable || stats.itemsAlreadyAvailable || 0 }}</div>
      <div class="text-xs sm:text-sm text-muted-foreground mt-1">Available</div>
    </div>
    <div class="text-center p-3 sm:p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
      <div class="text-2xl sm:text-3xl font-bold text-destructive">{{ stats.errors || stats.itemsErrors || stats.notFound || stats.itemsNotFound || 0 }}</div>
      <div class="text-xs sm:text-sm text-muted-foreground mt-1">{{ stats.errors || stats.itemsErrors ? 'Errors' : 'Not Found' }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  stats: {
    total?: number
    totalItems?: number
    requested?: number
    itemsRequested?: number
    alreadyRequested?: number
    itemsAlreadyRequested?: number
    alreadyAvailable?: number
    itemsAlreadyAvailable?: number
    notFound?: number
    itemsNotFound?: number
    errors?: number
    itemsErrors?: number
  }
}

defineProps<Props>()
</script>

