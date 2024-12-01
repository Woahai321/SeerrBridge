# 🌉 SeerrBridge - Automate Your Media Fetching with DMM 🎬

![seerrbridge-cover](https://github.com/user-attachments/assets/653eae72-538a-4648-b132-04faae3fb82e)

![GitHub last commit](https://img.shields.io/github/last-commit/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![GitHub issues](https://img.shields.io/github/issues/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![GitHub stars](https://img.shields.io/github/stars/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![GitHub release](https://img.shields.io/github/v/release/Woahai321/SeerrBridge?style=for-the-badge&logo=github)
![Python](https://img.shields.io/badge/Python-3.10.11+-blue?style=for-the-badge&logo=python)
[![Website](https://img.shields.io/badge/Website-soluify.com-blue?style=for-the-badge&logo=web)](https://soluify.com/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-connect-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/company/soluify/)


---

## 🚀 What is SeerrBridge?

🌉 **SeerrBridge** is a browser automation tool that integrates [Jellyseer](https://github.com/Fallenbagel/jellyseerr)/[Overseerr](https://overseerr.dev/) with [Debrid Media Manager](https://github.com/debridmediamanager/debrid-media-manager). It listens to movie requests via Overseerr webhook. It automates the torrent search and download process using Debrid Media Manager via browser automation, which in turn, gets sent to Real-Debrid. This streamlines your media management, making it fast and efficient.

🛠️ **Why SeerrBridge?** 

**SeerrBridge** eliminates the need to set up multiple applications like [Radarr](https://radarr.video/), [Sonarr](https://sonarr.tv/), [Jackett](https://github.com/Jackett/Jackett), [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr), and other download clients. With SeerrBridge, you streamline your media management into one simple, automated process. No more juggling multiple tools—just request and download!

Simply put, I was too lazy to set up all of these other applications (arrs) and thought.... I want this instead.


---

## 📊 Flowchart (Rectangle of Life)

![image](https://github.com/user-attachments/assets/e6b1a4f2-8c69-40f9-92a8-e6e76e8e34e7)

---

## 🔑 Key Features

- **Automated Movie Requests**: Automatically processes movie requests from Overseerr and fetches torrents from Debrid Media Manager.
- **Debrid Media Manager Integration**: Uses DMM to automate (via browser) torrent search & downloads.
- **Persistent Browser Session**: Keeps a browser session alive using Selenium, ensuring faster and more seamless automation.
- **Queue Management**: Handles multiple requests with an asynchronous queue, ensuring smooth processing.
- **Error Handling & Logging**: Provides comprehensive logging and error handling to ensure smooth operation.
- **Setting Custom Regex / Filter in Settings**: Upon launch, the script with automate the addition of a regex filter which can be updated in code.
---

## 📊 Compatibility

| Service        | Status | Notes                                |
|----------------|--------|--------------------------------------|
| **[List Sync](https://github.com/Woahai321/list-sync)**| ✅      | Our other Seerr app for importing lists   |
| **Jellyseerr**  | ✅      | Main integration. Supports movie requests via webhook  |
| **Overseerr**   | ✅      | Base application Jellyseerr is based on  |
| **Debrid Media Manager**| ✅      | Torrent fetching automation          |
| **Real-Debrid**| ✅      | Unrestricted (torrent) downloader       |
| **SuggestArr**| ✅      | Automatically grab related content and send to Jellyseerr/Overseerr      |
| **Windows & Linux**| ✅      | Tested and working in both Windows & Linux environments      |

---

### (THIS SCRIPT IS STILL IN BETA)

## ⚙ Requirements

Before you can run this script, ensure that you have the following prerequisites:

### 1. **Jellyseerr / Overseerr Notifications**
  - SeerrBridge should be running on the same machine that Jellyseerr / Overseerr is running on.
  - You will navigate to Settings > Notifications > Webhook > Turn it on, and configure as shown below

     ```bash
     http://localhost:8777/jellyseer-webhook/
     ```

![image](https://github.com/user-attachments/assets/170a2eb2-274a-4fc1-b288-5ada91a9fc47)

### 2. **Real-Debrid Account**
   - You will need a valid [Real-Debrid](https://real-debrid.com/) account to authenticate and interact with the Debrid Media Manager.
     - The Debrid Media Manager Access token, Client ID, Client Secret, & Refresh Tokens are used and should be set within your .env file. Grab this from your browser via Inspect > 

![image](https://github.com/user-attachments/assets/c718851c-60d4-4750-b020-a3edb990b53b)

This is what you want to copy from your local storage and set in your .env:

    {"value":"your_token","expiry":123} | YOUR_CLIENT_ID | YOUR_CLIENT_SECRET | YOUR_REFRESH_TOKEN

### 3. **ChromeDriver**
   - [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/) is required to automate browser tasks using Selenium.
     - Ensure that the version of ChromeDriver matches your installed version of Google Chrome.
       - Download it manually and provide the path in your `.env` file.

### 4. **Python 3.10.11+**
   - The bot requires **Python 3.10.11** or higher. You can download Python from [here](https://www.python.org/downloads/).

### 5. **Required Python Libraries**
   - You can install the required libraries by running:
     ```bash
     pip install -r requirements.txt
     ```

---

### Example `.env` File

Create a `.env` (or rename the example .env) file in the root directory of the project and add the following environment variables:

```bash
CHROMEDRIVER_PATH=path-to-chromedriver
RD_ACCESS_TOKEN={"value":"YOUR_TOKEN","expiry":123456789}
RD_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
RD_CLIENT_ID=YOUR_CLIENT_ID
RD_CLIENT_SECRET=YOUR_CLIENT_SECRET
TRAKT_API_KEY=YOUR_TRAKT_TOKEN
OVERSEERR_API_KEY=YOUR_OVERSEERR_TOKEN
OVERSEERR_BASE=https://YOUR_OVERSEERR_URL.COM
HEADLESS_MODE=true
ENABLE_AUTOMATIC_BACKGROUND_TASK=false
REFRESH_INTERVAL_MINUTES=120
TORRENT_FILTER_REGEX=^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
```

---

## 🛠️ Getting Started

### Sending Notifications to SeerrBridge from Jellyseerr / Overseerr

Configure your webhook as mentioned above so SeerrBridge can ingest and process approval requests.


### Python Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Woahai321/SeerrBridge.git
   cd SeerrBridge
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```bash
   python seerrbridge.py
   ```

---

### 🐳 Docker Support

#### Option 1: Using Docker Compose

1. Clone the repository:
    ```bash
    git clone https://github.com/Woahai321/SeerrBridge.git
    cd SeerrBridge
    ```

2. Copy the example `.env` file and update it with your specific configuration:
    ```bash
    cp .env.example .env
    ```

    Example `.env`:
    ```bash
    CHROMEDRIVER_PATH=path-to-chromedriver
    RD_ACCESS_TOKEN={"value":"YOUR_TOKEN","expiry":123456789}
    RD_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
    RD_CLIENT_ID=YOUR_CLIENT_ID
    RD_CLIENT_SECRET=YOUR_CLIENT_SECRET
    TRAKT_API_KEY=YOUR_TRAKT_TOKEN
    OVERSEERR_API_KEY=YOUR_OVERSEERR_TOKEN
    OVERSEERR_BASE=https://YOUR_OVERSEERR_URL.COM
    HEADLESS_MODE=true
    TORRENT_FILTER_REGEX=^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).*
    ```

3. Start the container:
    ```bash
    docker-compose up -d
    ```

4. Access the app at: [http://localhost:8777](http://localhost:8777).

---

#### Option 2: Using Docker Run

Skip Compose and run the container directly:

```bash
docker run -d \
  --name seerrbridge \
  -p 8777:8777 \
  -v $(pwd)/config:/app/config \
  -e CHROMEDRIVER_PATH=path-to-chromedriver \
  -e RD_ACCESS_TOKEN={"value":"YOUR_TOKEN","expiry":123456789} \
  -e RD_REFRESH_TOKEN=YOUR_REFRESH_TOKEN \
  -e RD_CLIENT_ID=YOUR_CLIENT_ID \
  -e RD_CLIENT_SECRET=YOUR_CLIENT_SECRET \
  -e TRAKT_API_KEY=YOUR_TRAKT_TOKEN \
  -e OVERSEERR_API_KEY=YOUR_OVERSEERR_TOKEN \
  -e OVERSEERR_BASE=https://YOUR_OVERSEERR_URL.COM \
  -e HEADLESS_MODE=true \
  -e TORRENT_FILTER_REGEX=^(?!.*【.*?】)(?!.*[\u0400-\u04FF])(?!.*\[esp\]).* \
  ghcr.io/woahai321/seerrbridge:main
```
---

That's it! Your **SeerrBridge** container should now be up and running. 🚀

---

## 🛤️ Roadmap

- [ ] **Faster Processing**: Implement concurrency to handle multiple requests simultaneously.
- [ ] **TV Show Support**: Extend functionality to handle TV series and episodes.
- [x] **DMM Token**: Ensure access token permanence/refresh
- [x] **Jellyseer/Overseer API Integration**: Direct integration with Jellyseer/Overseer API for smoother automation and control.
- [x] **Title Parsing**: Ensure torrent titles/names are properly matched and handle different languages.
- [x] **Docker Support**: Allow for Docker / Compose container.

---

## 🔍 How It Works

1. **Seerr Webhook**: SeerrBridge listens for movie requests via the configured webhook.
2. **Automated Search**: It uses Selenium to automate the search for movies on Debrid Media Manager site.
3. **Torrent Fetching**: Once a matching torrent is found, SeerrBridge automates the Real-Debrid download process.
4. **Queue Management**: Requests are added to a queue and processed one by one, ensuring smooth and efficient operation.

If you want to see the automation working in real-time, you can edit the .env and set it to false

![image](https://github.com/user-attachments/assets/dc1e9cdb-ff59-41fa-8a71-ccbff0f3c210)

This will launch a visible Chrome browser. Be sure not to mess with it while it's operating or else you will break the current action/script and need a re-run.

Example:

![Seerr](https://github.com/user-attachments/assets/cc61cb67-0f64-4172-bc10-9f32021f697a)

---

## 🎯 Custom Regex Filtering

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

---

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

## 💰 Donations

If you find SeerrBridge useful and would like to support its development, consider making a donation:

- BTC (Bitcoin): `bc1qxjpfszwvy3ty33weu6tjkr394uq30jwkysp4x0`
- ETH (Ethereum): `0xAF3ADE79B7304784049D200ea50352D1C717d7f2`

Thank you for your support!

---

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Woahai321/SeerrBridge&type=Date)](https://star-history.com/#Woahai321/SeerrBridge&Date)

---

## 📜 Legal Disclaimer

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

