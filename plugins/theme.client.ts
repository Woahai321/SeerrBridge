export default defineNuxtPlugin(() => {
  const colorMode = useColorMode()
  
  // Watch for theme changes and apply custom classes
  watch(() => colorMode.value, (newValue) => {
    if (process.client) {
      const html = document.documentElement
      html.classList.remove('dark', 'darth-vadarr')
      
      if (newValue === 'darth-vadarr') {
        html.classList.add('darth-vadarr')
      } else if (newValue === 'dark') {
        html.classList.add('dark')
      }
    }
  }, { immediate: true })
})

