# PDF Bot - Product Requirements Document

## Original Problem Statement
Build a Telegram-based PDF automation system where:
- User uploads PDF from iPhone via Telegram
- System compresses PDF (Ghostscript) and resizes to A4 (PyMuPDF)
- Optionally renames based on caption
- Sends optimized PDF back
- Target: <60s for 30MB, <2min for 100MB, supports up to 300MB

## Architecture
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
```

## User Personas
1. **Primary User**: Individual who needs to optimize PDFs from iPhone
   - Wants simple upload → receive workflow
   - No technical knowledge required
   - Values speed and simplicity

## Core Requirements (Static)
- [x] Pyrogram-based Telegram bot
- [x] Ghostscript compression (balanced mode)
- [x] PyMuPDF A4 resize (595x842)
- [x] Caption-based renaming
- [x] Support files up to 300MB
- [x] Docker deployment ready
- [x] Railway configuration

## What's Been Implemented
### 2026-01-XX - Initial MVP
- **bot.py**: Pyrogram Telegram bot with PDF handling
- **pdf_processor.py**: Ghostscript compression + PyMuPDF A4 resize
- **server.py**: FastAPI health check and stats API
- **main.py**: Combined entry point (bot + health server)
- **Dockerfile**: With Ghostscript installed
- **railway.json**: Railway deployment config
- **Frontend Dashboard**: Monitoring stats and logs

## Tech Stack
- Python 3.11
- Pyrogram + TgCrypto
- PyMuPDF (fitz)
- Ghostscript
- FastAPI (health checks)
- React (dashboard)
- Docker
- Railway

## Prioritized Backlog
### P0 - Critical (Done)
- [x] PDF compression
- [x] A4 resize
- [x] Telegram integration

### P1 - Important
- [ ] Deploy to Railway with actual credentials
- [ ] Test with real Telegram bot
- [ ] Performance testing with large files

### P2 - Nice to Have
- [ ] Progress feedback during processing
- [ ] Multiple compression modes
- [ ] Batch file processing
- [ ] Processing queue for concurrent users

## Next Tasks
1. Set Telegram credentials (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN) in Railway
2. Deploy to Railway using `railway up`
3. Test with actual PDF files from iPhone
4. Monitor processing times and optimize if needed
