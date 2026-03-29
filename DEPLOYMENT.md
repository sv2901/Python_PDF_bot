# PDF Bot Deployment Guide

## Railway Deployment

### Prerequisites
1. Railway account (https://railway.app)
2. Telegram Bot credentials:
   - API_ID and API_HASH from https://my.telegram.org
   - BOT_TOKEN from @BotFather

### Step-by-Step Deployment

#### 1. Create Railway Project
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init
```

#### 2. Set Environment Variables
In Railway dashboard or via CLI:
```bash
railway variables set TELEGRAM_API_ID=your_api_id
railway variables set TELEGRAM_API_HASH=your_api_hash
railway variables set TELEGRAM_BOT_TOKEN=your_bot_token
railway variables set MONGO_URL=mongodb://localhost:27017
railway variables set DB_NAME=pdf_bot
```

#### 3. Deploy
```bash
# Push to Railway
railway up
```

Or connect your GitHub repository in Railway dashboard for automatic deployments.

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| TELEGRAM_API_ID | Yes | From my.telegram.org |
| TELEGRAM_API_HASH | Yes | From my.telegram.org |
| TELEGRAM_BOT_TOKEN | Yes | From @BotFather |
| MONGO_URL | No | MongoDB connection (optional for stats) |
| DB_NAME | No | Database name (default: pdf_bot) |

### Docker Build (Local Testing)
```bash
# Build
docker build -t pdf-bot .

# Run
docker run -d \
  -e TELEGRAM_API_ID=your_id \
  -e TELEGRAM_API_HASH=your_hash \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -p 8001:8001 \
  pdf-bot
```

### Verification
1. Send /start to your bot
2. Upload a test PDF
3. Check Railway logs for processing status

### Performance Notes
- ~30MB PDF: Under 60 seconds
- ~100MB PDF: Under 2 minutes
- ~300MB PDF: 3-5 minutes (depends on complexity)

### Troubleshooting

#### Bot not responding
- Check Railway logs: `railway logs`
- Verify environment variables are set correctly
- Ensure bot token is valid

#### Processing fails
- Check Ghostscript is installed (docker logs)
- Verify temp directory permissions
- Check for corrupted PDF input

#### Slow downloads
- Pyrogram uses MTProto for direct server connection
- Large files benefit from Railway's network
- Consider file complexity (scanned vs native PDF)

### Architecture
```
iPhone/Telegram -> Telegram Servers -> Railway Container
                                           |
                                           v
                                    [Pyrogram Bot]
                                           |
                                           v
                                    [PDF Processor]
                                    (Ghostscript + PyMuPDF)
                                           |
                                           v
                                    [Upload Result]
                                           |
                                           v
                               iPhone receives optimized PDF
```
