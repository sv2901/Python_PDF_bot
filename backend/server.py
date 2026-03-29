from fastapi import FastAPI, APIRouter
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'pdf_bot')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Create the main app without a prefix
app = FastAPI(title="PDF Bot API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class ProcessingStats(BaseModel):
    total_processed: int = 0
    total_bytes_saved: int = 0
    total_bytes_saved_mb: float = 0
    uptime_seconds: int = 0
    bot_status: str = "unknown"

class ProcessingLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str
    output_filename: str
    original_size_bytes: int
    processed_size_bytes: int
    pages: int
    processing_time_seconds: float
    user_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error_message: Optional[str] = None


# Health check
@api_router.get("/")
async def root():
    return {"message": "PDF Bot API", "status": "online"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "service": "pdf-bot-api"}

# Stats endpoints
@api_router.get("/stats", response_model=ProcessingStats)
async def get_stats():
    """Get bot processing statistics."""
    # Count processed files
    total_processed = await db.processing_logs.count_documents({})
    
    # Calculate total bytes saved
    pipeline = [
        {"$group": {
            "_id": None,
            "total_original": {"$sum": "$original_size_bytes"},
            "total_processed": {"$sum": "$processed_size_bytes"}
        }}
    ]
    result = await db.processing_logs.aggregate(pipeline).to_list(1)
    
    total_bytes_saved = 0
    if result:
        total_bytes_saved = result[0].get("total_original", 0) - result[0].get("total_processed", 0)
    
    return ProcessingStats(
        total_processed=total_processed,
        total_bytes_saved=total_bytes_saved,
        total_bytes_saved_mb=round(total_bytes_saved / (1024 * 1024), 2),
        bot_status="running"
    )

@api_router.get("/logs", response_model=List[ProcessingLog])
async def get_logs(limit: int = 50):
    """Get recent processing logs."""
    logs = await db.processing_logs.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    for log in logs:
        if isinstance(log.get('timestamp'), str):
            log['timestamp'] = datetime.fromisoformat(log['timestamp'])
    
    return logs

@api_router.post("/logs", response_model=ProcessingLog)
async def create_log(log: ProcessingLog):
    """Record a processing log (called by bot)."""
    doc = log.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.processing_logs.insert_one(doc)
    return log

# Legacy status endpoints
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

# Dashboard HTML page
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Bot Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-card: #1a1a25;
            --text-primary: #f0f0f5;
            --text-secondary: #9090a0;
            --accent: #00d4aa;
            --border: #2a2a3a;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--text-secondary); margin-bottom: 2rem; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent);
        }
        .stat-label { color: var(--text-secondary); }
        .usage-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
        }
        .usage-box h2 { margin-bottom: 1rem; font-size: 1.2rem; }
        .usage-box ol { padding-left: 1.5rem; color: var(--text-secondary); }
        .usage-box li { padding: 0.3rem 0; }
        .refresh-btn {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            cursor: pointer;
            font-family: inherit;
            margin-bottom: 1.5rem;
        }
        .refresh-btn:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 PDF Bot Dashboard</h1>
        <p class="subtitle">Telegram PDF Optimizer</p>
        
        <button class="refresh-btn" onclick="loadStats()">🔄 Refresh</button>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="processed">-</div>
                <div class="stat-label">PDFs Processed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="saved">-</div>
                <div class="stat-label">MB Saved</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="status">-</div>
                <div class="stat-label">Bot Status</div>
            </div>
        </div>
        
        <div class="usage-box">
            <h2>📱 How to Use</h2>
            <ol>
                <li>Open Telegram on your phone</li>
                <li>Search for your PDF Bot</li>
                <li>Send any PDF file (up to 300MB)</li>
                <li>Choose: <strong>Compress Only</strong> or <strong>Compress + A4</strong></li>
                <li>Optionally rename the file</li>
                <li>Receive optimized PDF back!</li>
            </ol>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('processed').textContent = data.total_processed;
                document.getElementById('saved').textContent = data.total_bytes_saved_mb + ' MB';
                document.getElementById('status').textContent = data.bot_status;
            } catch (e) {
                console.error('Failed to load stats', e);
            }
        }
        loadStats();
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve dashboard HTML page."""
    return DASHBOARD_HTML

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()