export default defineEventHandler(async (event) => {
  return {
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'darthvadarr-nuxt',
    version: '1.0.0'
  }
})