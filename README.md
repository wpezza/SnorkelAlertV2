# 🌊 Snorkel Alert v2

**Perth's Smartest Beach & Snorkelling Forecast System**

Get intelligent 7-day forecasts for 15 Perth beaches from Fremantle to Hillarys. Know exactly when and where to go for perfect snorkelling or beach conditions.

![Dashboard Preview](https://img.shields.io/badge/Dashboard-Live-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Made with Claude](https://img.shields.io/badge/Made%20with-Claude-blueviolet)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🏖️ **15 Beaches** | Full coverage from Fremantle to Hillarys |
| 📅 **7-Day Forecast** | Plan your whole week |
| 🤿 **Snorkel Ratings** | Wave height, visibility, shelter analysis |
| ☀️ **Beach Ratings** | Wind, temperature, UV index |
| 🌡️ **Water Temperature** | Know what to wear |
| 🌊 **Tide Times** | Low tide = better snorkelling |
| 👥 **Crowd Predictions** | Avoid the masses |
| 🌅 **Sunrise Times** | Best light for early sessions |
| ⚠️ **UV Warnings** | Sun safety alerts |
| 💎 **Hidden Gem Picks** | Smart alternatives to busy spots |
| 📱 **Multi-Channel Alerts** | Pushover, Telegram, or Email |
| 📊 **Beautiful Dashboard** | GitHub Pages hosted |
| 🤖 **AI-Powered** | Claude analyses conditions intelligently |

---

## 🚀 Quick Start (10 minutes)

### Step 1: Fork This Repository

Click the **Fork** button at the top right of this page.

### Step 2: Get Your API Keys

#### Anthropic (Required)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account and add credits (~$5 will last months)
3. Go to **API Keys** → **Create Key**
4. Copy the key (starts with `sk-ant-...`)

#### Pushover (Recommended - $5 one-time)
1. Download **Pushover** app on your phone (iOS/Android) - $5
2. Create account at [pushover.net](https://pushover.net)
3. Copy your **User Key** from the dashboard
4. Click **Create Application** → name it "Snorkel Alert"
5. Copy the **API Token**

### Step 3: Add Secrets to GitHub

1. Go to your forked repo
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

| Secret Name | Value |
|-------------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `PUSHOVER_USER_KEY` | Your Pushover user key |
| `PUSHOVER_API_TOKEN` | Your Pushover app token |

### Step 4: Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **gh-pages** / **root**
4. Click **Save**

### Step 5: Run Your First Forecast

1. Go to **Actions** tab
2. Click **🌊 Beach Forecast**
3. Click **Run workflow** → **Run workflow**
4. Wait ~60 seconds
5. Check your phone for notification!
6. Visit `https://YOUR-USERNAME.github.io/snorkel-alert-v2/` for dashboard

---

## 📱 Notification Options

### Option 1: Pushover (Recommended)
- **Cost:** $5 one-time
- **Pros:** Instant push notifications, easy multi-user
- **Setup:** Buy app, create account, add secrets

### Option 2: Telegram (Free)
- **Cost:** Free
- **Pros:** Group chats, no cost
- **Setup:** Create bot via @BotFather

Add these secrets:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_IDS=123456789
```

Add this variable:
```
ENABLE_TELEGRAM=true
```

### Option 3: Email (Free)
- **Cost:** Free
- **Pros:** Beautiful HTML emails
- **Setup:** Use Gmail app password

Add these secrets:
```
EMAIL_ADDRESS=you@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_RECIPIENTS=you@gmail.com,friend@gmail.com
```

Add this variable:
```
ENABLE_EMAIL=true
```

---

## 👥 Adding Friends

### Pushover
1. They download the Pushover app ($5)
2. They create an account at pushover.net
3. They give you their **User Key**
4. Update your `PUSHOVER_USER_KEY` secret to: `your_key,their_key,another_key`

### Telegram
1. Create a group chat
2. Add your bot to the group
3. Anyone in the group gets forecasts

### Email
1. Add their email to `EMAIL_RECIPIENTS`: `you@gmail.com,friend@gmail.com`

---

## 🏖️ Beaches Covered

| Beach | Area | Best For |
|-------|------|----------|
| Bathers Beach | Fremantle | Cafes, calm swimming |
| South Beach | Fremantle | Dogs, families |
| Leighton Beach | North Fremantle | Dogs, bodysurfing |
| Cottesloe Beach | Cottesloe | Iconic sunsets, cafes |
| North Cottesloe | Cottesloe | Snorkelling (Peters Pool) |
| Swanbourne Beach | Swanbourne | Quiet, dogs (south) |
| City Beach | City Beach | Families, protected |
| Floreat Beach | Floreat | Quiet, boardwalk |
| Scarborough Beach | Scarborough | Surf, nightlife |
| Trigg Beach | Trigg | Surf, reef |
| Mettams Pool | Trigg | **Best snorkelling** |
| Watermans Bay | Watermans | Snorkelling, quiet |
| Sorrento Beach | Sorrento | Cafes, sunset |
| Hillarys Beach | Hillarys | Families, harbour |
| Boyinaboat Reef | Hillarys | Dive trail, snorkelling |

---

## ⏰ Schedule

Default: **Monday, Wednesday, Friday at 10am Perth time**

To change, edit `.github/workflows/forecast.yml`:

```yaml
schedule:
  # Daily at 6am Perth
  - cron: '0 22 * * *'
  
  # Weekdays at 7am Perth  
  - cron: '0 23 * * 1-5'
  
  # Every day at 10am Perth
  - cron: '0 2 * * *'
```

---

## 💰 Cost Breakdown

| Item | Cost |
|------|------|
| GitHub Actions | Free |
| Claude API | ~$0.01/forecast (~$0.15/month) |
| Pushover (optional) | $5 one-time per user |
| Telegram (optional) | Free |
| Email (optional) | Free |
| GitHub Pages | Free |

**Total: ~$5 setup + ~$0.15/month**

---

## 🔧 Customisation

### Add More Beaches

Edit `snorkel_alert.py` and add to `PERTH_BEACHES`:

```python
{
    "name": "Your Beach",
    "area": "Suburb",
    "lat": -31.9500,
    "lon": 115.7500,
    "type": "snorkel",  # or "beach" or "both"
    "shelter": ["E", "NE"],  # Protected from these wind directions
    "features": ["reef", "calm"],
    "crowd_factor": 0.5,  # 0-1, higher = busier
    "parking": "good",
    "facilities": ["toilets", "showers"],
}
```

### Change Notification Preferences

Add these variables in GitHub:

| Variable | Values | Description |
|----------|--------|-------------|
| `ENABLE_PUSHOVER` | `true`/`false` | Enable Pushover |
| `ENABLE_TELEGRAM` | `true`/`false` | Enable Telegram |
| `ENABLE_EMAIL` | `true`/`false` | Enable Email |

---

## 📊 Example Notification

```
🌊 Glassy midweek - Thursday's the pick!

Mixed start but conditions improve Thursday with sub-0.2m waves 
at Mettams Pool. Saturday looking good for Cottesloe sunbathing 
with light winds and 29°C.

🌡️ Water: 23°C - Refreshing, boardies fine

Thu: 🤿✨ ☀️ Glassy at Mettams til 9am, skip Cottesloe crowds
Fri: 🤿 ☀️ Light chop, try Watermans instead
Sat: 😐 ☀️✨ Waves up but perfect beach weather at Cottesloe
Sun: ❌ 💨 Sea breeze arriving early, stay home

🤿 Best snorkel: Mettams Pool (Thursday 6-9am)
☀️ Best beach: Cottesloe Beach (Saturday)
💎 Hidden gem: Watermans Bay (Friday) - quieter than Mettams
```

---

## ❓ Troubleshooting

### Workflow Failed
1. Go to **Actions** → click failed run → check logs
2. Common issues:
   - Missing `ANTHROPIC_API_KEY`
   - Invalid Pushover token
   - Rate limits (wait and retry)

### No Notification Received
1. Check the workflow logs for errors
2. Verify secrets are set correctly
3. Check Pushover/Telegram app is installed
4. Check spam folder for email

### Dashboard Not Loading
1. Ensure GitHub Pages is enabled
2. Wait 2-3 minutes after first deploy
3. Check **Actions** tab for deployment status

---

## 🤝 Contributing

PRs welcome! Ideas:
- More beaches (Rockingham, Mandurah, Rottnest)
- Surf conditions
- Fish/marine life predictions
- Historical accuracy tracking
- Calendar integration

---

## 📄 License

MIT License - do whatever you want with it!

---

## 🙏 Credits

- Weather data: [Open-Meteo](https://open-meteo.com) (free, no API key)
- AI: [Anthropic Claude](https://anthropic.com)
- Built with 🤿 in Perth, Western Australia

---

**Made for Will by Claude** 🌊🤿☀️
