# 🌉 SeerrBridge - Automate Your Media Fetching with DMM 🎬

![seerrbridge-cover](https://github.com/user-attachments/assets/653eae72-538a-4648-b132-04faae3fb82e)

![GitHub last commit](https://img.shields.io/github/last-commit/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![GitHub issues](https://img.shields.io/github/issues/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![GitHub stars](https://img.shields.io/github/stars/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![GitHub release](https://img.shields.io/github/v/release/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![Python](https://img.shields.io/badge/Python-3.10.11+-blue?style=for-the-badge&logo=python)
[![Website](https://img.shields.io/badge/Website-soluify.com-blue?style=for-the-badge&logo=web)](https://soluify.com/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-connect-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/company/soluify/)
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

---

## 🚀 What is SeerrBridge?

🌉 **SeerrBridge** is a browser automation tool that integrates [Jellyseer](https://github.com/Fallenbagel/jellyseerr)/[Overseerr](https://overseerr.dev/) with [Debrid Media Manager](https://github.com/debridmediamanager/debrid-media-manager). It listens to movie requests via Overseerr webhook. It automates the torrent search and download process using Debrid Media Manager via browser automation, which in turn, gets sent to Real-Debrid. This streamlines your media management, making it fast and efficient.

<details>
<summary>🛠️ Why SeerrBridge?</summary>

**SeerrBridge** eliminates the need to set up multiple applications like [Radarr](https://radarr.video/), [Sonarr](https://sonarr.tv/), [Jackett](https://github.com/Jackett/Jackett), [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr), and other download clients. With SeerrBridge, you streamline your media management into one simple, automated process. No more juggling multiple tools—just request and download!

Simply put, I was too lazy to set up all of these other applications (arrs) and thought.... I want this instead.

Example:

![sb](https://github.com/user-attachments/assets/f4a9f1c9-5fa9-4fa5-b1e8-3ddc6a156a91)
</details>

---

<details>
<summary>📊 Flowchart (Rectangle of Life)</summary>

![image](https://github.com/user-attachments/assets/e6b1a4f2-8c69-40f9-92a8-e6e76e8e34e7)
</details>


<details>
<summary>🔑 Key Features</summary>

- **Automated Movie Requests**: Automatically processes movie requests from Overseerr and fetches torrents from Debrid Media Manager.
  
- **TV Show Subscriptions**: Subscribes to ongoing/currently airing TV shows and automatically tracks individual episode releases.
  - Automatically fetches individual episodes when **complete season packs** are unavailable.
  - Tracks previously missed or failed episodes and retries processing them.
  - Continuously polls on a defined interval to automatically detect and fetch new episodes as they are released.
  - Fully integrated with **Debrid Media Manager** and **Real-Debrid**.

- **Debrid Media Manager Integration**: Uses DMM to automate (via browser) torrent search & downloads.
  
- **Persistent Browser Session**: Keeps a browser session alive using Selenium, ensuring faster and more seamless automation.
  
- **Queue Management**: Handles multiple requests with an asynchronous queue, ensuring smooth processing.
  
- **Error Handling & Logging**: Provides comprehensive logging and error handling to ensure smooth operation.
  
- **Setting Custom Regex / Filter in Settings**: Upon launch, the script automates the addition of a regex filter which can be updated in code.
</details>

<details>
<summary>🌉 Darth Vadarr (SeerrBridge Dashboard) - NEW FEATURE🌟</summary>

## What is Darth Vadarr?

Darth Vadarr is a modern, feature-rich web dashboard built with **Nuxt 4** and **Vue 3** that provides a comprehensive visual interface to monitor, manage, and control your SeerrBridge media automation. It replaces the need for command-line tools and log files, offering an intuitive web-based experience.

![image](https://github.com/user-attachments/assets/0f49edb0-0ade-4c40-9dbd-3c65d542091b)

### 🎯 Core Features

#### **Dashboard Overview**
- **Real-time Status Monitoring**: Live view of SeerrBridge service status, uptime, and health metrics
- **Statistics Cards**: Animated cards displaying key metrics including:
  - Total processed media (movies & TV shows)
  - Currently processing items
  - Success/failure counts
  - Queue status and activity
- **Currently Processing Section**: Real-time view of items being processed with detailed status information
- **Recent Media Feed**: Chronological view of recently processed media with thumbnails and metadata

#### **Processed Media Management**
- **Comprehensive Media Library**: Browse all processed movies and TV shows with advanced filtering
- **Search & Filter**: 
  - Search by title, year, or metadata
  - Filter by status (completed, processing, failed, pending)
  - Filter by media type (movie, TV show)
  - Filter by processing stage
- **Media Details**: 
  - Detailed information for each media item
  - Season and episode tracking for TV shows
  - Processing history and status
  - Retry/retrigger functionality for failed items
- **Bulk Operations**: Manage multiple media items at once

#### **Search & Discovery**
- **Overseerr Integration**: Search for movies and TV shows directly from Overseerr
- **Grid & List Views**: Toggle between visual grid and detailed list views
- **Media Details**: View comprehensive information before processing
- **Quick Actions**: Request media directly from the dashboard

#### **Collections Browser**
- **Franchise Collections**: Browse movies organized by franchise (e.g., Marvel Cinematic Universe, Star Wars)
- **Collection Details**: View all movies in a franchise with metadata
- **Search Collections**: Find collections by name or movie title
- **Random Discovery**: Discover new collections with random suggestions

#### **Logs & Monitoring**
- **Categorized Logs**: View logs by type:
  - All logs (comprehensive view)
  - Errors only
  - Critical errors
  - Success logs
  - Failed episodes
- **Real-time Updates**: Live log streaming with automatic refresh
- **Log Filtering**: Filter logs by level, type, and time range
- **Pagination**: Navigate through large log files efficiently

#### **Settings & Configuration**
- **API Credentials Management**: 
  - Real-Debrid configuration (Client ID, Client Secret, Access Token, Refresh Token)
  - Trakt API key
  - Overseerr/Jellyseerr API key and base URL
- **Application Settings**:
  - Headless mode toggle
  - Automatic background task enablement
  - Show subscription task control
  - Refresh interval configuration
- **Torrent Filtering**:
  - Preset regex patterns
  - Custom regex builder
  - Regex pattern testing
- **Size Limits**:
  - Maximum movie size settings
  - Maximum episode size settings
- **Database Management**: View and manage database connections and status
- **Theme Support**: Light, dark, and system theme options

#### **Setup Wizard**
- **Guided Initial Setup**: Step-by-step wizard for first-time configuration
- **Credential Testing**: Test API credentials before saving
- **Configuration Validation**: Ensure all required settings are properly configured

### 🎨 User Experience Features

- **Responsive Design**: Fully responsive interface that works on desktop, tablet, and mobile devices
- **Dark/Light Themes**: Multiple theme options with system preference detection
- **Real-time Updates**: Live data updates without manual refresh
- **Smooth Animations**: Polished UI with smooth transitions and loading states
- **Error Handling**: Graceful error handling with user-friendly messages
- **Performance Optimized**: Built with Nuxt 4 for optimal performance and SEO

### 🔌 Technical Integration

Darth Vadarr connects directly to your SeerrBridge backend via REST API, providing:
- **Secure Communication**: All API calls are authenticated and encrypted
- **Database Integration**: Direct connection to MySQL database for real-time data
- **WebSocket Support**: Real-time updates where applicable
- **Caching**: Intelligent data caching for improved performance

### 📍 Access

To access Darth Vadarr, navigate to **`http://localhost:3777`** after starting the Docker containers.

The dashboard automatically connects to your SeerrBridge backend running on port 8777, providing seamless integration between the frontend and backend services.
</details>

<details>
<summary>📊 Compatibility</summary>

| Service        | Status | Notes                                |
|----------------|--------|--------------------------------------|
| **[List Sync](https://github.com/Woahai321/list-sync)**| ✅      | Our other Seerr app for importing lists   |
| **Jellyseerr**  | ✅      | Main integration. Supports movie requests via webhook  |
| **Overseerr**   | ✅      | Base application Jellyseerr is based on  |
| **Debrid Media Manager**| ✅      | Torrent fetching automation          |
| **Real-Debrid**| ✅      | Unrestricted (torrent) downloader       |
| **AllDebrid**| ❌      | Not Supported      |
| **TorBox**| ❌      | Not Supported     |
| **SuggestArr**| ✅      | Automatically grab related content and send to Jellyseerr/Overseerr      |
| **Windows & Linux x86-64**| ✅      | Tested and working in both Windows & Linux environments      |
</details>

<details>
### (THIS SCRIPT IS STILL IN BETA)
<summary>⚙ Requirements</summary>

Before you can run this script, ensure that you have the following prerequisites:

### 1. **Jellyseerr / Overseerr API & Notifications**
  - SeerrBridge should be running on the same machine that Jellyseerr / Overseerr is running on.
  - You will need the API key for your .env file.
  - For notifications, navigate to Settings > Notifications > Webhook > Turn it on, and configure as shown below

     ```bash
     http://localhost:8777/jellyseer-webhook/
     ```

![image](https://github.com/user-attachments/assets/170a2eb2-274a-4fc1-b288-5ada91a9fc47)

Ensure your JSON payload is the following 

```
{
    "notification_type": "{{notification_type}}",
    "event": "{{event}}",
    "subject": "{{subject}}",
    "message": "{{message}}",
    "image": "{{image}}",
    "{{media}}": {
        "media_type": "{{media_type}}",
        "tmdbId": "{{media_tmdbid}}",
        "tvdbId": "{{media_tvdbid}}",
        "status": "{{media_status}}",
        "status4k": "{{media_status4k}}"
    },
    "{{request}}": {
        "request_id": "{{request_id}}",
        "requestedBy_email": "{{requestedBy_email}}",
        "requestedBy_username": "{{requestedBy_username}}",
        "requestedBy_avatar": "{{requestedBy_avatar}}",
        "requestedBy_settings_discordId": "{{requestedBy_settings_discordId}}",
        "requestedBy_settings_telegramChatId": "{{requestedBy_settings_telegramChatId}}"
    },
    "{{issue}}": {
        "issue_id": "{{issue_id}}",
        "issue_type": "{{issue_type}}",
        "issue_status": "{{issue_status}}",
        "reportedBy_email": "{{reportedBy_email}}",
        "reportedBy_username": "{{reportedBy_username}}",
        "reportedBy_avatar": "{{reportedBy_avatar}}",
        "reportedBy_settings_discordId": "{{reportedBy_settings_discordId}}",
        "reportedBy_settings_telegramChatId": "{{reportedBy_settings_telegramChatId}}"
    },
    "{{comment}}": {
        "comment_message": "{{comment_message}}",
        "commentedBy_email": "{{commentedBy_email}}",
        "commentedBy_username": "{{commentedBy_username}}",
        "commentedBy_avatar": "{{commentedBy_avatar}}",
        "commentedBy_settings_discordId": "{{commentedBy_settings_discordId}}",
        "commentedBy_settings_telegramChatId": "{{commentedBy_settings_telegramChatId}}"
    },
    "{{extra}}": []
}
```

Notification Types should also be set to "Request Automatically Approved", and your user should be set to automatic approvals.

![image](https://github.com/user-attachments/assets/46df5e43-b9c3-48c9-aa22-223c6720ca15)

![image](https://github.com/user-attachments/assets/ae25b2f2-ac80-4c96-89f2-c47fc936debe)


### 2. **Real-Debrid Account**
   - You will need a valid [Real-Debrid](https://real-debrid.com/) account to authenticate and interact with the Debrid Media Manager.
     - The Debrid Media Manager Access token, Client ID, Client Secret, & Refresh Tokens are used and should be set within your .env file. Grab this from your browser via Inspect > 

![image](https://github.com/user-attachments/assets/c718851c-60d4-4750-b020-a3edb990b53b)

This is what you want to copy from your local storage and set in your .env:

    RD_ACCESS_TOKEN={"value":"your_token","expiry":123}
    RD_CLIENT_ID=YOUR_CLIENT_ID
    RD_CLIENT_SECRET=YOUR_CLIENT_SECRET
    RD_REFRESH_TOKEN=YOUR_REFRESH_TOKEN

### 3. **Trakt API / Client ID**
   - Create a [Trakt.tv](https://Trakt.tv) account. Navigate to Settings > Your API Apps > New Application
     - You can use https://google.com as the redirect URI
     - Save the Client ID for your .env file.
    
![image](https://github.com/user-attachments/assets/c5eb7dbf-7785-45ca-99fa-7e6341744c9d)
![image](https://github.com/user-attachments/assets/3bb77fd5-2c8f-4675-a1da-59f0cb9cb178)


---

### Example `.env` File

Create a `.env` file in the root directory of the project. The following environment variables are used for Docker setup:

```bash
# Database Configuration (Required)
DB_NAME=seerrbridge
DB_USER=seerrbridge
DB_PASSWORD=seerrbridge
DB_ROOT_PASSWORD=seerrbridge_root

# Encryption Master Key (Recommended for production)
# If not set, a temporary key will be generated (data lost on restart)
SEERRBRIDGE_MASTER_KEY=your_master_key_here

# Real-Debrid Configuration
RD_ACCESS_TOKEN={"value":"YOUR_TOKEN","expiry":123456789}
RD_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
RD_CLIENT_ID=YOUR_CLIENT_ID
RD_CLIENT_SECRET=YOUR_CLIENT_SECRET

# Trakt API Configuration
TRAKT_API_KEY=YOUR_TRAKT_TOKEN

# Overseerr/Jellyseerr Configuration
OVERSEERR_API_KEY=YOUR_OVERSEERR_TOKEN
OVERSEERR_BASE=https://YOUR_OVERSEERR_URL.COM

# Application Settings
HEADLESS_MODE=true
ENABLE_AUTOMATIC_BACKGROUND_TASK=true
ENABLE_SHOW_SUBSCRIPTION_TASK=true
REFRESH_INTERVAL_MINUTES=120
TORRENT_FILTER_REGEX=^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
MAX_MOVIE_SIZE=0
MAX_EPISODE_SIZE=0
```

**Note**: Most configuration (API keys, tokens, advanced settings, etc.) can be managed via the web interface and is stored securely in the database. Only database credentials and the master key need to be in the `.env` file.
</details>

<details>
<summary>🛠️ Getting Started</summary>

### Sending Notifications to SeerrBridge from Jellyseerr / Overseerr

Configure your webhook as mentioned above so SeerrBridge can ingest and process approval requests.


---

### 🐳 Docker Setup

SeerrBridge consists of three main components:
- **MySQL Database**: Stores application data and configuration
- **SeerrBridge Backend**: Python/FastAPI application that handles webhooks and automation
- **Darth Vadarr Dashboard**: Nuxt.js frontend for monitoring and managing SeerrBridge

The recommended way to run SeerrBridge is using Docker Compose.

## Prerequisites
- Docker and Docker Compose installed on your system
- A `.env` file with your configuration (see example below)

### Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Woahai321/SeerrBridge.git
   cd SeerrBridge
   ```

2. **Create or edit your `.env` file** in the project root:

```bash
# Database Configuration (Required)
DB_NAME=seerrbridge
DB_USER=seerrbridge
DB_PASSWORD=seerrbridge
DB_ROOT_PASSWORD=seerrbridge_root

# Encryption Master Key (Recommended for production)
# If not set, a temporary key will be generated (data lost on restart)
SEERRBRIDGE_MASTER_KEY=your_master_key_here

# Real-Debrid Configuration
RD_ACCESS_TOKEN={"value":"YOUR_TOKEN","expiry":123456789}
RD_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
RD_CLIENT_ID=YOUR_CLIENT_ID
RD_CLIENT_SECRET=YOUR_CLIENT_SECRET

# Trakt API Configuration
TRAKT_API_KEY=YOUR_TRAKT_TOKEN

# Overseerr/Jellyseerr Configuration
OVERSEERR_API_KEY=YOUR_OVERSEERR_TOKEN
OVERSEERR_BASE=https://YOUR_OVERSEERR_URL.COM

# Application Settings
HEADLESS_MODE=true
ENABLE_AUTOMATIC_BACKGROUND_TASK=true
ENABLE_SHOW_SUBSCRIPTION_TASK=true
REFRESH_INTERVAL_MINUTES=120
TORRENT_FILTER_REGEX=^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
MAX_MOVIE_SIZE=0
MAX_EPISODE_SIZE=0
```

**Note**: All configuration (API keys, tokens, advanced settings, etc.) can also be managed via the web interface and is stored securely in the database. Only database credentials and the master key need to be in the `.env` file.

3. **Start the containers**:

```bash
docker compose -f docker-compose.local.yml up -d
```

4. **Access the applications**:
   - SeerrBridge API: [http://localhost:8777](http://localhost:8777)
   - Darth Vadarr Dashboard: [http://localhost:3777](http://localhost:3777)
   - MySQL Database: `localhost:3307` (if you need direct database access)

### Configuration Notes

- **Volumes**: The configuration creates persistent volumes for:
  - MySQL data (`mysql_data`)
  - Application logs (`./logs`)
  - Application data (`./data`)
- **Networks**: All containers are placed on the same network (`seerrbridge-network`) so they can communicate
- **Health Checks**: All services include health checks to ensure proper startup order
- **Restart Policy**: Containers will restart automatically unless manually stopped
- **Database Initialization**: The MySQL container automatically initializes the database schema on first run

### Docker Compose File Structure

The `docker-compose.local.yml` file includes:

```yaml
services:
  mysql:              # MySQL 8.0 database
  seerrbridge:        # SeerrBridge backend (Python/FastAPI)
  darthvadarr-nuxt:   # Darth Vadarr dashboard (Nuxt.js)
```

### Viewing Logs

To view logs from all services:
```bash
docker compose -f docker-compose.local.yml logs -f
```

To view logs from a specific service:
```bash
docker compose -f docker-compose.local.yml logs -f seerrbridge
docker compose -f docker-compose.local.yml logs -f darthvadarr-nuxt
docker compose -f docker-compose.local.yml logs -f mysql
```

### Stopping the Services

To stop all services:
```bash
docker compose -f docker-compose.local.yml down
```

To stop and remove volumes (⚠️ **This will delete all data**):
```bash
docker compose -f docker-compose.local.yml down -v
```

---

### Docker Network Configuration for Webhooks

If you're running both Overseerr/Jellyseerr and SeerrBridge in Docker, you have two options for configuring the webhook:

#### Option 1: Use Docker Network (Recommended)
If both containers are on the same Docker network, use the container name:
```
http://seerrbridge-app:8777/jellyseer-webhook/
```

#### Option 2: Use Host Network
If Overseerr/Jellyseerr is running on the host machine, use:
```
http://localhost:8777/jellyseer-webhook/
```

#### Option 3: Use Container IP
If you need to use the container IP address:

1. **Find the container ID**:
   ```bash
   docker ps
   ```

2. **Get the container IP**:
   ```bash
   docker inspect seerrbridge-app | grep IPAddress
   ```

3. **Use the IP in your webhook URL**:
   ```
   http://CONTAINER_IP:8777/jellyseer-webhook/
   ```

---



### Connecting to External Docker Networks

If you need to connect SeerrBridge to an existing Docker network (e.g., to communicate with Overseerr/Jellyseerr running in another Docker Compose setup):

1. **Check existing networks:**
   ```bash
   docker network ls
   ```

2. **Connect SeerrBridge to the external network:**
   ```bash
   docker network connect EXTERNAL_NETWORK_NAME seerrbridge-app
   ```

3. **Update your webhook URL** to use the container name:
   ```
   http://seerrbridge-app:8777/jellyseer-webhook/
   ```

Alternatively, you can modify `docker-compose.local.yml` to use an external network:

```yaml
networks:
  seerrbridge-network:
    external: true
    name: your_existing_network_name
```

---

That's it! Your **SeerrBridge** containers should now be up and running. 🚀
</details>

<details>
<summary>🛤️ Roadmap</summary>

- [ ] **Faster Processing**: Implement concurrency to handle multiple requests simultaneously.
- [x] **TV Show Support**: Extend functionality to handle TV series and episodes.
- [x] **DMM Token**: Ensure access token permanence/refresh
- [x] **Jellyseer/Overseer API Integration**: Direct integration with Jellyseer/Overseer API for smoother automation and control.
- [x] **Title Parsing**: Ensure torrent titles/names are properly matched and handle different languages.
- [x] **Docker Support**: Allow for Docker / Compose container.
</details>

<details>
<summary>🔍 How It Works</summary>

1. **Seerr Webhook**: SeerrBridge listens for movie requests via the configured webhook.
2. **Automated Search**: It uses Selenium to automate the search for movies on Debrid Media Manager site.
3. **Torrent Fetching**: Once a matching torrent is found, SeerrBridge automates the Real-Debrid download process.
4. **Queue Management**: Requests are added to a queue and processed one by one, ensuring smooth and efficient operation.

If you want to see the automation working in real-time, you can edit the .env and set it to false

![image](https://github.com/user-attachments/assets/dc1e9cdb-ff59-41fa-8a71-ccbff0f3c210)

This will launch a visible Chrome browser. Be sure not to mess with it while it's operating or else you will break the current action/script and need a re-run.

Example:

![sb](https://github.com/user-attachments/assets/c6a0ee1e-db07-430c-93cd-f282c8f0888f)
</details>

<details>
<summary>📺 TV Show Subscription Feature</summary>

SeerrBridge now includes an exciting **TV Show Subscription** feature that enhances its functionality for ongoing and currently airing TV shows! With this new addition, SeerrBridge takes automated media fetching to the next level:

### 🔧 How It Works:
- **Episode-Level Automation**: Automatically tracks and fetches **individual episodes** for ongoing TV shows, especially when a **complete season pack** is unavailable.
- **Smart Subscription System**:
    - Tracks currently airing episodes and **checks for new releases on a defined interval**.
    - Handles previously **missed or failed episode downloads**, ensuring nothing gets left behind.
- **Seamless Integration**: Works flawlessly with **Debrid Media Manager** and **Real-Debrid**, providing uninterrupted automation and caching requested episodes instantly when available.
- **Fully Automated**: Once subscribed to a show, SeerrBridge manages all episodes for you. No need to manually check for new episodes!

### 🌟 Key Benefits:
- **Never Miss an Episode**: Perfect for keeping up with currently airing shows where season packs are rare or unavailable during release cycles.
- **Optimized for Real-Debrid**: Ensures episodes are downloaded as soon as torrents are cached and accessible in your debrid account.
- **Retry Mechanism**: Any failed episode attempts are logged and automatically retried during the next interval check.

🎉 **This feature ensures you stay up to date on your favorite series—all fully automated!**
</details>

<details>
<summary>📁 Movie and Show File Sizes</summary>

For movies, possible values are: 
| Value | Description |
| :-----------: | :-----------: |
| 0| Biggest Size Possible |
|1|1 GB|
|3|3 GB|
|5|5 GB **(Default)**|
|15|15 GB|
|30|30 GB|
|60|60 GB|

For episodes, possible values are: 
| Value | Description |
| :-----------: | :-----------: |
| 0| Biggest Size Possible |
|0.1|100 MB|
|0.3|300 MB|
|0.5|500 MB|
|1|1 GB **(Default)**|
|3|3 GB|
|5|5 GB|
</details>

<details>
<summary>🎯 Custom Regex Filtering</summary>

This script includes support for **custom regex filtering**, allowing you to filter out unwanted items and refine the results based on specific patterns. The regex is automatically added when the script runs, and you can customize it directly in the code.

### Default Regex

The currently used regex is:

```python
^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

#### What It Does:
- **Exclude Items with `【...】`**: `(?!.*【.*?】)` removes items with formatted text in this style.
- **Exclude Cyrillic Characters**: `(?!.*[\u0400-\u04FF])` removes items containing characters from Cyrillic scripts (e.g., Russian text).
- **Exclude Items with `[esp]`**: `(?!.*\[esp\])` removes items explicitly marked as `[esp]` (often denoting Spanish content).
- **Match All Other Content**: `.*` ensures the filter applies to the rest of the string.

This is a broad exclusion-based filter that removes unwanted patterns without requiring specific inclusions.

---

### Optional Regex (Filtering by Resolution)

If you'd like to refine the filter further to only match items containing **1080p** or **2160p**, you can use the following optional regex:

```python
^(?=.*(1080p|2160p))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

#### What It Does:
- **Include Only Items with `1080p` or `2160p`**: `(?=.*(1080p|2160p))` ensures that only items with these resolutions are processed.
- The rest of the filter (**exclude `【...】`, Cyrillic characters, or `[esp]`**) works the same as in the default regex.

---

### How to Use

To switch between the default and optional regex, simply update the `.env` file:

- **Default Regex**:
    ```python
    ^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
    ```

- **Optional Regex**:
    ```python
    ^(?=.*(1080p|2160p))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
    ```

This gives you flexibility to define what gets filtered, based on your preferred criteria.


## 📜 List of Regex Examples

Below is a categorized list of regex patterns for different filtering possibilities.

---

### 1. **Current Filter**
```regex
^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

---

### 2. **Current Filter with Resolutions**
```regex
^(?=.*(1080p|2160p))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

---

### 3. **Current Filter with Torrent Types**
```regex
^(?=.*(Remux|BluRay|BDRip|BRRip))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

---

### 4. **Filter with Both Types and Resolutions**
```regex
^(?=.*(1080p|2160p))(?=.*(Remux|BluRay|BDRip|BRRip))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

---

### 5. **Filter for Specific Resolution Only**
```regex
^(?=.*(1080p|2160p)).*
```

---

### 6. **Filter for Specific Torrent Types Only**
```regex
^(?=.*(Remux|BluRay|BDRip|BRRip)).*
```

---

### 7. **Customizable Regex Template**
```regex
^(?=.*(1080p|2160p))?(?=.*(Remux|BluRay|BDRip|BRRip))?(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

---

By selecting one of these patterns, you can tailor the regex filter to fit your exact needs.
</details>


## 📞 Contact

Have any questions or need help? Feel free to [open an issue](https://github.com/Woahai321/SeerrBridge/issues) or connect with us on [LinkedIn](https://www.linkedin.com/company/soluify/).

---

## 🤝 Contributing

We welcome contributions! Here’s how you can help:

1. **Fork the repository** on GitHub.
2. **Create a new branch** for your feature or bug fix.
3. **Commit your changes**.
4. **Submit a pull request** for review.

---

## 💰 Support SeerrBridge's Development

If you find SeerrBridge useful and would like to support its development, consider becoming a sponsor:

➡️ [Sponsor us on GitHub](https://github.com/sponsors/Woahai321)

Thank you for your support!

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Woahai321/SeerrBridge&type=Date)](https://star-history.com/#Woahai321/SeerrBridge&Date)

---

## Contributors 🌟

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/KRadd1221"><img src="https://avatars.githubusercontent.com/u/5341534?v=4?s=100" width="100px;" alt="Kevin"/><br /><sub><b>Kevin</b></sub></a><br /><a href="https://github.com/Woahai321/SeerrBridge/commits?author=KRadd1221" title="Code">💻</a> <a href="https://github.com/Woahai321/SeerrBridge/issues?q=author%3AKRadd1221" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/shivamsnaik"><img src="https://avatars.githubusercontent.com/u/16705944?v=4?s=100" width="100px;" alt="Shivam Naik"/><br /><sub><b>Shivam Naik</b></sub></a><br /><a href="https://github.com/Woahai321/SeerrBridge/commits?author=shivamsnaik" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jacobmejilla"><img src="https://avatars.githubusercontent.com/u/112974356?v=4?s=100" width="100px;" alt="jacobmejilla"/><br /><sub><b>jacobmejilla</b></sub></a><br /><a href="https://github.com/Woahai321/SeerrBridge/commits?author=jacobmejilla" title="Code">💻</a> <a href="#ideas-jacobmejilla" title="Ideas, Planning, & Feedback">🤔</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://www.funkypenguin.co.nz"><img src="https://avatars.githubusercontent.com/u/1524686?v=4?s=100" width="100px;" alt="David Young"/><br /><sub><b>David Young</b></sub></a><br /><a href="https://github.com/Woahai321/SeerrBridge/commits?author=funkypenguin" title="Documentation">📖</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

---

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

<details>
<summary>📜 Legal Disclaimer</summary>

This repository and the accompanying software are intended **for educational purposes only**. The creators and contributors of this project do not condone or encourage the use of this tool for any illegal activities, including but not limited to copyright infringement, illegal downloading, or torrenting copyrighted content without proper authorization.

### Usage of the Software:
- **SeerrBridge** is designed to demonstrate and automate media management workflows. It is the user's responsibility to ensure that their usage of the software complies with all applicable laws and regulations in their country.
- The tool integrates with third-party services which may have their own terms of service. Users must adhere to the terms of service of any external platforms or services they interact with.

### No Liability:
- The authors and contributors of this project are not liable for any misuse or claims that arise from the improper use of this software. **You are solely responsible** for ensuring that your use of this software complies with applicable copyright laws and other legal restrictions.
- **We do not provide support or assistance for any illegal activities** or for bypassing any security measures or protections.

### Educational Purpose:
This tool is provided as-is, for **educational purposes**, and to help users automate the management of their own legally obtained media. It is **not intended** to be used for pirating or distributing copyrighted material without permission.

If you are unsure about the legality of your actions, you should consult with a legal professional before using this software.
</details>