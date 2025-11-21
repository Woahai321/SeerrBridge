# Darth Vadarr - SeerrBridge Dashboard

A beautiful, modern dashboard for monitoring and managing your SeerrBridge service, built with Vue 3, Nuxt 3, and TypeScript.

## Features

- 🎨 **Modern Glass-morphism Design** - Beautiful, cohesive UI with glass effects and smooth animations
- 📊 **Real-time Dashboard** - Live monitoring of SeerrBridge status and statistics
- 📝 **Comprehensive Logging** - View and filter logs with advanced search capabilities
- 🔔 **Smart Notifications** - Real-time notifications for important events
- ⚙️ **Settings Management** - Configure your SeerrBridge connection and preferences
- 📱 **Responsive Design** - Works perfectly on desktop, tablet, and mobile devices
- 🌙 **Dark/Light Theme** - Automatic theme switching with system preference support
- 🚀 **Performance Optimized** - Built with Vue 3 Composition API and Nuxt 3 for optimal performance

## Tech Stack

- **Frontend**: Vue 3, Nuxt 3, TypeScript
- **Styling**: Tailwind CSS with custom glass-morphism components
- **Icons**: Lucide Vue (via Nuxt Icon)
- **State Management**: Pinia
- **API**: Nuxt Server API routes
- **Build Tool**: Vite (via Nuxt)

## Getting Started

### Prerequisites

- Docker and Docker Compose
- OR Node.js 18+ and npm/yarn (for local development)

> **Important**: For first-time setup, please read the [Database Setup Guide](DATABASE_SETUP.md) to ensure proper database initialization.

### Option 1: Docker Setup (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd darthvadarr-nuxt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the setup script:
```bash
# Linux/Mac
chmod +x setup-docker.sh
./setup-docker.sh

# Windows
setup-docker.bat
```

4. Access the application:
   - **Frontend**: http://localhost:3000
   - **SeerrBridge API**: http://localhost:8777
   - **MySQL Database**: localhost:3307

### Option 2: Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd darthvadarr-nuxt
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start the development server:
```bash
npm run dev
```

5. Open your browser and navigate to `http://localhost:3000`

### Docker Commands

```bash
# Start all services
docker-compose -f docker-compose.nuxt.yml up -d

# View logs
docker-compose -f docker-compose.nuxt.yml logs -f

# Stop services
docker-compose -f docker-compose.nuxt.yml down

# Rebuild and start
docker-compose -f docker-compose.nuxt.yml up --build -d

# Development mode (with hot reload)
docker-compose -f docker-compose.dev.yml up -d
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SEERRBRIDGE_URL` | URL of your SeerrBridge service | `http://localhost:8777` |

### Settings

The dashboard includes a comprehensive settings panel where you can configure:

- **General Settings**: Refresh intervals, auto-refresh, theme preferences
- **Notifications**: Enable/disable notifications, select notification types, sound settings
- **Bridge Configuration**: SeerrBridge URL, connection timeout, test connection
- **Log Configuration**: Log levels, max entries, retention period

## API Endpoints

The dashboard provides several API endpoints for data fetching:

- `GET /api/bridge-status` - Get SeerrBridge status
- `POST /api/bridge-reload` - Reload SeerrBridge configuration
- `GET /api/logs` - Get log statistics and recent logs
- `GET /api/logs/entries` - Get paginated log entries
- `GET /api/env` - Get environment variables (redacted)
- `GET /api/validate-url` - Validate URL accessibility

## Development

### Project Structure

```
├── assets/           # Global assets (CSS, images)
├── components/       # Vue components
├── composables/      # Vue composables for reusable logic
├── layouts/          # Layout components
├── pages/            # Application pages
├── server/           # Server API routes
├── types/            # TypeScript type definitions
└── nuxt.config.ts    # Nuxt configuration
```

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on GitHub or contact the development team.

---

Built with ❤️ using Vue 3, Nuxt 3, and TypeScript