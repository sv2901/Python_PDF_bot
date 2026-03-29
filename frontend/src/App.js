import React, { useState, useEffect } from 'react';
import { FileText, TrendingDown, Clock, Activity, RefreshCw, Smartphone, CheckCircle, AlertCircle } from 'lucide-react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsRes, logsRes] = await Promise.all([
        fetch(`${API_URL}/api/stats`),
        fetch(`${API_URL}/api/logs?limit=20`)
      ]);
      
      if (!statsRes.ok || !logsRes.ok) {
        throw new Error('Failed to fetch data');
      }
      
      const statsData = await statsRes.json();
      const logsData = await logsRes.json();
      
      setStats(statsData);
      setLogs(logsData);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const calculateSavings = (original, processed) => {
    if (original === 0) return 0;
    return Math.round(((original - processed) / original) * 100);
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <FileText className="logo-icon" />
            <div>
              <h1>PDF Bot Dashboard</h1>
              <p className="subtitle">Telegram PDF Optimizer</p>
            </div>
          </div>
          <button 
            className="refresh-btn"
            onClick={fetchData}
            disabled={loading}
            data-testid="refresh-button"
          >
            <RefreshCw className={loading ? 'spinning' : ''} size={18} />
            Refresh
          </button>
        </div>
      </header>

      <main className="main">
        {error && (
          <div className="error-banner" data-testid="error-banner">
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        <section className="hero">
          <div className="hero-content">
            <Smartphone className="hero-icon" />
            <h2>How to Use</h2>
            <ol className="usage-steps">
              <li>Open Telegram on your iPhone</li>
              <li>Search for your PDF Bot</li>
              <li>Send any PDF file (up to 300MB)</li>
              <li>Optionally add a caption to rename</li>
              <li>Receive optimized A4 PDF back!</li>
            </ol>
          </div>
        </section>

        <section className="stats-grid" data-testid="stats-section">
          <div className="stat-card">
            <div className="stat-icon">
              <FileText />
            </div>
            <div className="stat-content">
              <span className="stat-value" data-testid="total-processed">
                {stats?.total_processed ?? '-'}
              </span>
              <span className="stat-label">PDFs Processed</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon savings">
              <TrendingDown />
            </div>
            <div className="stat-content">
              <span className="stat-value" data-testid="bytes-saved">
                {stats?.total_bytes_saved_mb ?? '-'} MB
              </span>
              <span className="stat-label">Total Space Saved</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon status">
              <Activity />
            </div>
            <div className="stat-content">
              <span className={`stat-value ${stats?.bot_status === 'running' ? 'online' : ''}`} data-testid="bot-status">
                {stats?.bot_status ?? 'Unknown'}
              </span>
              <span className="stat-label">Bot Status</span>
            </div>
          </div>
        </section>

        <section className="logs-section" data-testid="logs-section">
          <h3>Recent Processing Logs</h3>
          {logs.length === 0 ? (
            <div className="empty-state">
              <Clock size={48} />
              <p>No processing logs yet</p>
              <span>Send a PDF to your Telegram bot to get started</span>
            </div>
          ) : (
            <div className="logs-table-container">
              <table className="logs-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>File</th>
                    <th>Original</th>
                    <th>Processed</th>
                    <th>Savings</th>
                    <th>Pages</th>
                    <th>Time</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} data-testid={`log-row-${log.id}`}>
                      <td>
                        {log.success ? (
                          <CheckCircle className="success-icon" size={18} />
                        ) : (
                          <AlertCircle className="error-icon" size={18} />
                        )}
                      </td>
                      <td className="filename">{log.output_filename}</td>
                      <td>{formatBytes(log.original_size_bytes)}</td>
                      <td>{formatBytes(log.processed_size_bytes)}</td>
                      <td className="savings-cell">
                        {calculateSavings(log.original_size_bytes, log.processed_size_bytes)}%
                      </td>
                      <td>{log.pages}</td>
                      <td>{log.processing_time_seconds?.toFixed(1)}s</td>
                      <td>{formatDate(log.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {lastUpdated && (
          <p className="last-updated" data-testid="last-updated">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        )}
      </main>

      <footer className="footer">
        <p>PDF Bot Dashboard &bull; Powered by Pyrogram + Ghostscript + PyMuPDF</p>
      </footer>
    </div>
  );
}

export default App;
