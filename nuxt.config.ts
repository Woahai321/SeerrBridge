// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  devtools: { enabled: true },
  compatibilityDate: '2024-11-01',
  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/color-mode',
    '@nuxtjs/google-fonts',
    '@pinia/nuxt',
    '@nuxt/icon'
  ],
  
  // TypeScript configuration
  typescript: {
    strict: true,
    typeCheck: false // Disable type checking in development to avoid vue-tsc issues
  },

  // CSS configuration
  css: ['~/assets/css/main.css'],

  // App configuration
  app: {
    head: {
      title: 'Darth Vadarr - SeerrBridge Dashboard',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Monitor and manage your SeerrBridge service with ease' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
      ]
    }
  },

  // Runtime config
  runtimeConfig: {
    // Private keys (only available on server-side)
    seerrbridgeUrl: process.env.SEERRBRIDGE_URL || 'http://localhost:8777',
    dbHost: process.env.DB_HOST || 'localhost',
    dbPort: process.env.DB_PORT || '3307',
    dbName: process.env.DB_NAME || 'seerrbridge',
    dbUser: process.env.DB_USER || 'seerrbridge',
    dbPassword: process.env.DB_PASSWORD || 'seerrbridge',
    
    // Public keys (exposed to client-side)
    public: {
      apiBase: '/api'
    }
  },

  // Color mode configuration
  colorMode: {
    preference: 'dark',
    fallback: 'dark',
    classSuffix: ''
  },

  // Google Fonts
  googleFonts: {
    families: {
      Outfit: [300, 400, 500, 600, 700]
    },
    display: 'swap'
  },

  // Tailwind CSS
  tailwindcss: {
    config: {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            border: 'hsl(var(--border))',
            input: 'hsl(var(--input))',
            ring: 'hsl(var(--ring))',
            background: 'hsl(var(--background))',
            foreground: 'hsl(var(--foreground))',
            primary: {
              DEFAULT: 'hsl(var(--primary))',
              foreground: 'hsl(var(--primary-foreground))'
            },
            secondary: {
              DEFAULT: 'hsl(var(--secondary))',
              foreground: 'hsl(var(--secondary-foreground))'
            },
            destructive: {
              DEFAULT: 'hsl(var(--destructive))',
              foreground: 'hsl(var(--destructive-foreground))'
            },
            muted: {
              DEFAULT: 'hsl(var(--muted))',
              foreground: 'hsl(var(--muted-foreground))'
            },
            accent: {
              DEFAULT: 'hsl(var(--accent))',
              foreground: 'hsl(var(--accent-foreground))'
            },
            popover: {
              DEFAULT: 'hsl(var(--popover))',
              foreground: 'hsl(var(--popover-foreground))'
            },
            card: {
              DEFAULT: 'hsl(var(--card))',
              foreground: 'hsl(var(--card-foreground))'
            },
            success: 'hsl(var(--success))',
            warning: 'hsl(var(--warning))',
            info: 'hsl(var(--info))'
          },
          borderRadius: {
            lg: 'var(--radius)',
            md: 'calc(var(--radius) - 2px)',
            sm: 'calc(var(--radius) - 4px)'
          },
          animation: {
            'gradient': 'gradient 15s ease infinite',
            'fade-in': 'fadeIn 0.5s ease-in-out',
            'pulse-soft': 'pulseSoft 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            'shimmer': 'shimmer 5.5s infinite',
            'shimmer-subtle': 'shimmerSubtle 60s cubic-bezier(0.4, 0.0, 0.2, 1) infinite'
          }
        }
      }
    }
  },

  // Server-side rendering
  ssr: true,

  // Build configuration
  build: {
    transpile: ['@headlessui/vue']
  },

  // Nitro configuration for preview mode
  nitro: {
    preset: 'node-server',
    // Exclude large directories from Nitro's file scanning
    // Specifically exclude images directory to avoid scanning 16,670+ image files
    ignore: [
      'data/**',
      'data/images/**',
      'data/images/movies/**',
      'seerr/**',
      'scripts/**',
      'mysql-init/**'
    ]
  },

  // Development server configuration
  devServer: {
    port: 3000,
    host: '0.0.0.0'
  },

  // Development configuration for hot reloading
  dev: process.env.NODE_ENV === 'development',
  
  // Vite configuration for better development experience
  vite: {
    server: {
      watch: {
        // Disable polling in Docker - use native events when possible
        // Polling causes major slowdowns with 16,670+ image files
        usePolling: process.env.CHOKIDAR_USEPOLLING === 'true',
        interval: process.env.CHOKIDAR_USEPOLLING === 'true' ? 3000 : undefined,
        binaryInterval: process.env.CHOKIDAR_USEPOLLING === 'true' ? 3000 : undefined,
        // Aggressively exclude large data directories from file watching
        // Use glob patterns that match both Windows and Unix paths
        ignored: [
          '**/data/**',
          '**/data/images/**',
          '**/data/images/movies/**',
          '**/node_modules/**',
          '**/.nuxt/**',
          '**/.output/**',
          '**/seerr/**',
          '**/scripts/**',
          '**/mysql-init/**',
          '**/logs/**',
          // Exclude image file extensions explicitly
          '**/*.webp',
          '**/*.jpg',
          '**/*.jpeg',
          '**/*.png',
          '**/*.gif'
        ],
        // Only watch specific directories
        followSymlinks: false
      },
      hmr: {
        port: 3000,
        host: '0.0.0.0'
      },
      // Reduce file system operations
      fs: {
        strict: false,
        // Deny access to files outside the project root except node_modules
        deny: ['**/data/images/**']
      }
    },
    optimizeDeps: {
      include: ['vue', 'vue-router', '@vueuse/core'],
      // Exclude data files from dependency optimization
      exclude: ['data'],
      // Force pre-bundling to reduce compilation time
      force: false
    },
  },

  // Auto-imports configuration
  imports: {
    dirs: [
      'composables/**'
    ]
  },

})
