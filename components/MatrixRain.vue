<template>
  <div 
    ref="matrixContainer"
    class="matrix-rain fixed inset-0 pointer-events-none overflow-hidden z-0"
    :class="{ 'dark': isDark }"
  >
    <canvas ref="canvas" class="absolute inset-0 w-full h-full" />
  </div>
</template>

<script setup lang="ts">
interface Particle {
  x: number
  y: number
  string: string // String of 3-5 characters (1s and 0s)
  opacity: number
  speed: number
  fadeIn: boolean
  fadeOut: boolean
  life: number
  maxLife: number
  waveOffset: number // For wave effect
}

const canvas = ref<HTMLCanvasElement | null>(null)
const matrixContainer = ref<HTMLDivElement | null>(null)
const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')
const isDarthVadarr = computed(() => colorMode.value === 'darth-vadarr')

// Configuration
const fontSize = 18
const particles: Particle[] = []
let animationId: number | null = null
let lastSpawnTime = 0
const spawnInterval = 200 // Spawn new particles every 200ms (sporadic)
let frameCount = 0

// Characters to use - just 1s and 0s
const chars = '10'

// Initialize canvas
const initCanvas = () => {
  if (!canvas.value || !process.client) return
  
  const ctx = canvas.value.getContext('2d')
  if (!ctx) return
  
  // Set canvas size
  canvas.value.width = window.innerWidth
  canvas.value.height = window.innerHeight
  
  // Clear particles on resize
  particles.length = 0
}

// Generate random string of 1s and 0s
const generateString = (): string => {
  const length = 3 + Math.floor(Math.random() * 3) // 3-5 characters
  let str = ''
  for (let i = 0; i < length; i++) {
    str += chars[Math.floor(Math.random() * chars.length)]
  }
  return str
}

// Create a new particle
const createParticle = (): Particle => {
  const canvasWidth = canvas.value?.width || window.innerWidth
  const canvasHeight = canvas.value?.height || window.innerHeight
  
  return {
    x: Math.random() * canvasWidth, // Random X across entire width
    y: Math.random() * canvasHeight, // Random Y across entire height
    string: generateString(), // String of 3-5 random 1s and 0s
    opacity: 0, // Start invisible (fade in)
    speed: 0.1 + Math.random() * 0.15, // Very slow, random speed
    fadeIn: true,
    fadeOut: false,
    life: 0,
    maxLife: 3000 + Math.random() * 4000, // 3-7 seconds lifespan
    waveOffset: Math.random() * Math.PI * 2 // Random wave phase
  }
}

// Draw matrix rain
const draw = (timestamp: number) => {
  if (!canvas.value || !process.client) {
    animationId = requestAnimationFrame(draw)
    return
  }
  
  const ctx = canvas.value.getContext('2d')
  if (!ctx) {
    animationId = requestAnimationFrame(draw)
    return
  }
  
  frameCount++
  
  // Clear canvas completely - no persistent shadow
  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)
  
  // Spawn new particles sporadically
  if (timestamp - lastSpawnTime > spawnInterval || lastSpawnTime === 0) {
    // Very sporadic spawning - sometimes none, sometimes 1-3
    if (Math.random() > 0.3) {
      const spawnCount = Math.random() > 0.7 ? (Math.random() > 0.5 ? 3 : 2) : 1
      for (let i = 0; i < spawnCount; i++) {
        particles.push(createParticle())
      }
    }
    lastSpawnTime = timestamp
  }
  
  // Theme-aware color: purple for SeerrBridge, red for Darth Vadarr
  const neonColor = isDarthVadarr.value 
    ? 'rgba(233, 32, 37, 1)' // Red #E92025 for Darth Vadarr
    : 'rgba(130, 36, 227, 1)' // Purple #8224E3 for SeerrBridge
  
  ctx.font = `bold ${fontSize}px 'Courier New', monospace`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  
  // Update and draw particles
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]
    
    // Update life (based on frame count for consistency)
    p.life += 16.67 // ~60fps timing
    
    // Fade in phase
    if (p.fadeIn && p.opacity < 1) {
      p.opacity += 0.02 // Slow fade in
      if (p.opacity >= 1) {
        p.fadeIn = false
        p.opacity = 1
      }
    }
    
    // Check if should start fading out
    if (!p.fadeOut && p.life > p.maxLife * 0.6) {
      // Random chance to start fading out early
      if (Math.random() > 0.95 || p.life > p.maxLife * 0.8) {
        p.fadeOut = true
      }
    }
    
    // Fade out phase
    if (p.fadeOut) {
      p.opacity -= 0.015 // Slow fade out
    }
    
    // Move down slowly (or stay in place for some particles)
    // Some particles move, some stay relatively still for variety
    if (Math.random() > 0.3) {
      p.y += p.speed
    } else {
      // Some particles drift slightly
      p.y += p.speed * 0.3
    }
    
    // Draw string vertically with wave effect
    if (p.opacity > 0.01) {
      const charSpacing = fontSize * 1.2 // Vertical spacing between characters
      const time = frameCount * 0.05 // Time for wave animation
      
      // Calculate starting Y position (center the string vertically)
      const stringHeight = (p.string.length - 1) * charSpacing
      const startY = p.y - (stringHeight / 2)
      
      // Draw each character in the string vertically with wave fade effect
      for (let j = 0; j < p.string.length; j++) {
        const char = p.string[j]
        const charY = startY + (j * charSpacing)
        
        // Wave effect: each character has different opacity based on position
        const wavePhase = p.waveOffset + (j * 0.8) + (time * 0.5)
        const waveOpacity = (Math.sin(wavePhase) + 1) / 2 // 0 to 1
        const charOpacity = p.opacity * (0.3 + waveOpacity * 0.7) // 30% to 100% of particle opacity
        
        if (charOpacity > 0.01) {
          // Outer glow
          ctx.shadowBlur = 12
          ctx.shadowColor = isDarthVadarr.value
            ? `rgba(233, 32, 37, ${charOpacity * 0.6})`
            : `rgba(130, 36, 227, ${charOpacity * 0.6})`
          ctx.fillStyle = neonColor.replace('1)', `${charOpacity * 0.8})`)
          ctx.fillText(char, p.x, charY)
          
          // Inner bright text
          ctx.shadowBlur = 0
          ctx.fillStyle = neonColor.replace('1)', `${charOpacity})`)
          ctx.fillText(char, p.x, charY)
        }
      }
    }
    
    // Remove particles that are off screen or fully faded
    const canvasHeight = canvas.value?.height || window.innerHeight
    if (p.y > canvasHeight + 50 || p.opacity <= 0 || p.life > p.maxLife) {
      particles.splice(i, 1)
    }
  }
  
  animationId = requestAnimationFrame(draw)
}

// Handle resize
const handleResize = () => {
  if (!canvas.value) return
  initCanvas()
}

onMounted(() => {
  if (!process.client) return
  
  initCanvas()
  lastSpawnTime = 0
  frameCount = 0
  
  // Pre-populate with some particles across the screen
  const initialParticleCount = 15
  for (let i = 0; i < initialParticleCount; i++) {
    const p = createParticle()
    // Start some with random opacity for variety
    if (Math.random() > 0.5) {
      p.opacity = Math.random() * 0.5 + 0.3
      p.fadeIn = false
    }
    particles.push(p)
  }
  
  animationId = requestAnimationFrame(draw)
  
  window.addEventListener('resize', handleResize)
  
  onUnmounted(() => {
    if (animationId) {
      cancelAnimationFrame(animationId)
    }
    window.removeEventListener('resize', handleResize)
    particles.length = 0
  })
})

// Watch for theme changes to restart animation
watch([isDark, isDarthVadarr], () => {
  if (canvas.value && process.client) {
    const ctx = canvas.value.getContext('2d')
    if (ctx) {
      // Clear and restart
      ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)
    }
  }
})
</script>

<style scoped>
.matrix-rain {
  opacity: 1; /* Full visibility for neon effect */
  z-index: 0;
}

.matrix-rain canvas {
  image-rendering: -webkit-optimize-contrast;
  image-rendering: crisp-edges;
  will-change: contents; /* Optimize for animation */
}
</style>
