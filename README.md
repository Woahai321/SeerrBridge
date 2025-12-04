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

🌉 **SeerrBridge** is a browser automation tool that integrates [Jellyseer](https://github.com/Fallenbagel/jellyseerr)/[Overseerr](https://overseerr.dev/) with [Debrid Media Manager](https://github.com/debridmediamanager/debrid-media-manager). It listens to movie requests via Overseerr webhook and automates the torrent search and download process using Debrid Media Manager via browser automation, which in turn gets sent to Real-Debrid. This streamlines your media management, making it fast and efficient.

---

## ⚡ Quick Start (1 Command!)

Just run this single command to get started. Docker will automatically pull the image if needed.

### Linux/Mac:
```bash
docker run -d --name seerrbridge --restart unless-stopped -p 3777:3777 -p 8777:8777 -p 8778:8778 -p 3307:3306 -v seerrbridge_mysql_data:/var/lib/mysql -v $(pwd)/logs:/app/logs -v $(pwd)/data:/app/data ghcr.io/woahai321/seerrbridge:latest
```

### Windows PowerShell:
```powershell
docker run -d --name seerrbridge --restart unless-stopped -p 3777:3777 -p 8777:8777 -p 8778:8778 -p 3307:3306 -v seerrbridge_mysql_data:/var/lib/mysql -v ${PWD}/logs:/app/logs -v ${PWD}/data:/app/data ghcr.io/woahai321/seerrbridge:latest
```

**That's it!** Access the dashboard at **http://localhost:3777**

> ⚠️ **Security Warning:** This uses default passwords and is **NOT recommended** to expose publicly on the internet.

**View logs:** `docker logs -f seerrbridge` | **Stop:** `docker stop seerrbridge && docker rm seerrbridge`

---

<details>
<summary>🔑 Key Features</summary>

- **Automated Movie Requests**: Processes movie requests from Overseerr and fetches torrents via Debrid Media Manager
- **TV Show Subscriptions**: Automatically tracks and fetches individual episodes for ongoing shows
- **Debrid Media Manager Integration**: Browser automation for torrent search & downloads
- **Modern Web Dashboard**: Built-in Darth Vadarr dashboard (Nuxt 4/Vue 3) for monitoring and management
- **Queue Management**: Asynchronous queue handling for smooth processing
- **Custom Regex Filtering**: Filter unwanted content via web interface
- **Persistent Browser Session**: Faster automation with Selenium session management
</details>

<details>
<summary>🛠️ Why SeerrBridge?</summary>

**SeerrBridge** eliminates the need to set up multiple applications like [Radarr](https://radarr.video/), [Sonarr](https://sonarr.tv/), [Jackett](https://github.com/Jackett/Jackett), [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr), and other download clients. With SeerrBridge, you streamline your media management into one simple, automated process. No more juggling multiple tools—just request and download!

Simply put, I was too lazy to set up all of these other applications (arrs) and thought.... I want this instead.

![sb](https://github.com/user-attachments/assets/f4a9f1c9-5fa9-4fa5-b1e8-3ddc6a156a91)
</details>

<details>
<summary>🌉 Darth Vadarr Dashboard</summary>

Modern web dashboard built with **Nuxt 4** and **Vue 3** providing a comprehensive visual interface to monitor, manage, and control your SeerrBridge automation.

**Key Features:**
- Real-time status monitoring and statistics
- Processed media library with advanced filtering
- Search & discovery with Overseerr integration
- Franchise collections browser
- Categorized logs and monitoring
- Settings & configuration management
- Responsive design with dark/light themes

Access at **http://localhost:3777** after starting the container.

<img width="2528" height="1286" alt="image" src="https://github.com/user-attachments/assets/4d7dd3f7-711b-4c3f-beda-cb0de6e0767e" />

</details>

<details>
<summary>🔍 How It Works</summary>

1. **Seerr Webhook**: SeerrBridge listens for movie requests via the configured webhook.
2. **Automated Search**: It uses Selenium to automate the search for movies on Debrid Media Manager site.
3. **Torrent Fetching**: Once a matching torrent is found, SeerrBridge automates the Real-Debrid download process.
4. **Queue Management**: Requests are added to a queue and processed one by one, ensuring smooth and efficient operation.

If you want to see the automation working in real-time, you can edit the .env and set `HEADLESS_MODE=false`. This will launch a visible Chrome browser. Be sure not to mess with it while it's operating or else you will break the current action/script and need a re-run.

![image](https://github.com/user-attachments/assets/dc1e9cdb-ff59-41fa-8a71-ccbff0f3c210)

Example:

![sb](https://github.com/user-attachments/assets/c6a0ee1e-db07-430c-93cd-f282c8f0888f)
</details>

<details>
<summary>📊 Compatibility</summary>

| Service        | Status | Notes                                |
|----------------|--------|--------------------------------------|
| **Jellyseerr/Overseerr**  | ✅      | Main integration via webhook  |
| **Debrid Media Manager**| ✅      | Torrent fetching automation          |
| **Real-Debrid**| ✅      | Unrestricted downloader       |
| **List Sync**| ✅      | Our other Seerr app for importing lists   |
| **SuggestArr**| ✅      | Auto-grab related content      |
| **AllDebrid/TorBox**| ❌      | Not Supported     |
| **Windows & Linux x86-64**| ✅      | Tested and working      |
</details>

---

## 🛠️ Configuration & Requirements

> ⚠️ **Note:** This script is still in BETA

Most configuration can be managed via the web dashboard at **http://localhost:3777** after starting the container. However, you'll need to set up the following prerequisites:

### 1. **Jellyseerr / Overseerr API & Notifications**

- SeerrBridge should be running on the same machine that Jellyseerr / Overseerr is running on
- You will need the API key for your .env file (or configure via web dashboard)
- For notifications, navigate to **Settings > Notifications > Webhook > Turn it on**, and configure as shown below:

     ```bash
     http://localhost:8777/jellyseer-webhook/
     ```

![image](https://github.com/user-attachments/assets/170a2eb2-274a-4fc1-b288-5ada91a9fc47)

Ensure your JSON payload is the following:

```json
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

Notification Types should also be set to **"Request Automatically Approved"**, and your user should be set to automatic approvals.

![image](https://github.com/user-attachments/assets/46df5e43-b9c3-48c9-aa22-223c6720ca15)

![image](https://github.com/user-attachments/assets/ae25b2f2-ac80-4c96-89f2-c47fc936debe)

### 2. **Real-Debrid Account**

- You will need a valid [Real-Debrid](https://real-debrid.com/) account to authenticate and interact with the Debrid Media Manager
- The Debrid Media Manager Access token, Client ID, Client Secret, & Refresh Tokens are used and should be set within your .env file or via the web dashboard
- Grab this from your browser via **Inspect > Application > Local Storage**

![image](https://github.com/user-attachments/assets/c718851c-60d4-4750-b020-a3edb990b53b)

This is what you want to copy from your local storage and set in your .env:

```
    RD_ACCESS_TOKEN={"value":"your_token","expiry":123}
    RD_CLIENT_ID=YOUR_CLIENT_ID
    RD_CLIENT_SECRET=YOUR_CLIENT_SECRET
    RD_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
```

### 3. **Trakt API / Client ID**

- Create a [Trakt.tv](https://Trakt.tv) account. Navigate to **Settings > Your API Apps > New Application**
- You can use `https://google.com` as the redirect URI
- Save the Client ID for your .env file or web dashboard
    
![image](https://github.com/user-attachments/assets/c5eb7dbf-7785-45ca-99fa-7e6341744c9d)
![image](https://github.com/user-attachments/assets/3bb77fd5-2c8f-4675-a1da-59f0cb9cb178)

**Note**: Most configuration (API keys, tokens, advanced settings, etc.) can be managed via the web interface and is stored securely in the database. Only database credentials and the master key need to be in the `.env` file.

### Docker Network Configuration for Webhooks

If you're running both Overseerr/Jellyseerr and SeerrBridge in Docker:

- **Same Docker network:** Use `http://seerrbridge:8777/jellyseer-webhook/`
- **Host machine:** Use `http://localhost:8777/jellyseer-webhook/`
- **Different networks:** Connect containers to the same network or use host IP

---

## 📺 Features & Settings

### TV Show Subscriptions

Automatically tracks and fetches individual episodes for ongoing TV shows:
- Episode-level automation when season packs unavailable
- Smart subscription system with interval checking
- Automatic retry for missed/failed episodes
- Fully integrated with Debrid Media Manager & Real-Debrid

### File Size Limits

**Movies:** 0 (unlimited), 1, 3, 5 (default), 15, 30, 60 GB  
**Episodes:** 0 (unlimited), 0.1, 0.3, 0.5, 1 (default), 3, 5 GB

### Custom Regex Filtering

Filter unwanted content using regex patterns. Default excludes:
- Items with `【...】` formatting
- Cyrillic characters
- Items marked `[esp]`

**Default Regex:**
```regex
^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

**With Resolution Filter:**
```regex
^(?=.*(1080p|2160p))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

<details>
<summary>📜 More Regex Examples</summary>

- **With Torrent Types**: `^(?=.*(Remux|BluRay|BDRip|BRRip))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*`
- **Types + Resolutions**: `^(?=.*(1080p|2160p))(?=.*(Remux|BluRay|BDRip|BRRip))(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*`
- **Resolution Only**: `^(?=.*(1080p|2160p)).*`
- **Types Only**: `^(?=.*(Remux|BluRay|BDRip|BRRip)).*`
</details>

---

<details>
<summary>🛤️ Roadmap</summary>

- [ ] **Faster Processing**: Implement concurrency to handle multiple requests simultaneously
- [x] **TV Show Support**: Extend functionality to handle TV series and episodes
- [x] **DMM Token**: Ensure access token permanence/refresh
- [x] **Jellyseer/Overseer API Integration**: Direct integration for smoother automation
- [x] **Title Parsing**: Proper matching and handling of different languages
- [x] **Docker Support**: Docker / Compose container support
</details>

<details>
<summary>📊 Flowchart (Rectangle of Life)</summary>

![image](https://github.com/user-attachments/assets/e6b1a4f2-8c69-40f9-92a8-e6e76e8e34e7)
</details>

---

## 📞 Contact

Have any questions or need help? Feel free to [open an issue](https://github.com/Woahai321/SeerrBridge/issues) or connect with us on [LinkedIn](https://www.linkedin.com/company/soluify/).

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository** on GitHub
2. **Create a new branch** for your feature or bug fix
3. **Commit your changes**
4. **Submit a pull request** for review

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
