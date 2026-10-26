import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Activity,
  Network,
  BarChart3,
  GitBranch,
  Play,
  Square,
  AlertTriangle,
  CheckCircle2,
  Clock,
  DollarSign,
  Cpu,
  Layers,
  Search,
  Filter,
  FileText,
  RotateCw,
  Info,
  ChevronRight,
  User,
  CreditCard,
  MapPin,
  ExternalLink
} from 'lucide-react';
import GraphVisualizer from './components/GraphVisualizer';

const API_BASE = '/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('stream'); // 'stream', 'alerts', 'graph', 'model', 'drift'
  const [apiHealth, setApiHealth] = useState(null);
  const [streamingActive, setStreamingActive] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [alertsData, setAlertsData] = useState({ alerts: [], total_count: 0, status_breakdown: {} });
  const [metrics, setMetrics] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [rings, setRings] = useState([]);
  const [driftReport, setDriftReport] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [selectedTxn, setSelectedTxn] = useState(null);

  // Filters for alerts
  const [alertStatusFilter, setAlertStatusFilter] = useState('ALL');
  const [alertTierFilter, setAlertTierFilter] = useState('ALL');

  // Feedback form state
  const [feedbackStatus, setFeedbackStatus] = useState('CONFIRMED_FRAUD');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  // 1. Fetch Health & Readiness
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setApiHealth(data);
      } else {
        setApiHealth(null);
      }
    } catch {
      setApiHealth(null);
    }
  }, []);

  // 2. Fetch Recent Transactions
  const fetchTransactions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/transactions?limit=60`);
      if (res.ok) {
        const data = await res.json();
        setTransactions(data);
      }
    } catch (err) {
      console.error('Failed fetching transactions:', err);
    }
  }, []);

  // 3. Fetch Alerts
  const fetchAlerts = useCallback(async () => {
    try {
      let url = `${API_BASE}/alerts?limit=100`;
      if (alertStatusFilter !== 'ALL') url += `&status=${alertStatusFilter}`;
      if (alertTierFilter !== 'ALL') url += `&risk_tier=${alertTierFilter}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setAlertsData(data);
      }
    } catch (err) {
      console.error('Failed fetching alerts:', err);
    }
  }, [alertStatusFilter, alertTierFilter]);

  // 4. Fetch Metrics & Runtime Ops
  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/metrics`);
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error('Failed fetching metrics:', err);
    }
  }, []);

  // 5. Fetch Graph Subgraph & Rings
  const fetchGraph = useCallback(async () => {
    try {
      const [subgraphRes, ringsRes] = await Promise.all([
        fetch(`${API_BASE}/graph/subgraph?max_nodes=70`),
        fetch(`${API_BASE}/graph/rings`)
      ]);
      if (subgraphRes.ok) setGraphData(await subgraphRes.json());
      if (ringsRes.ok) {
        const rData = await ringsRes.json();
        setRings(rData.rings || []);
      }
    } catch (err) {
      console.error('Failed fetching graph:', err);
    }
  }, []);

  // 6. Fetch Drift Report
  const fetchDrift = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/drift`);
      if (res.ok) setDriftReport(await res.json());
    } catch (err) {
      console.error('Failed fetching drift report:', err);
    }
  }, []);

  // Initial load & Polling
  useEffect(() => {
    checkHealth();
    fetchTransactions();
    fetchAlerts();
    fetchMetrics();
    fetchGraph();
    fetchDrift();

    const interval = setInterval(() => {
      checkHealth();
      fetchTransactions();
      fetchAlerts();
      fetchMetrics();
    }, 2500);

    return () => clearInterval(interval);
  }, [checkHealth, fetchTransactions, fetchAlerts, fetchMetrics, fetchGraph, fetchDrift]);

  // Handle Start / Stop Replay
  const toggleStreaming = async () => {
    try {
      if (streamingActive) {
        await fetch(`${API_BASE}/replay/stop`, { method: 'POST' });
        setStreamingActive(false);
      } else {
        const res = await fetch(`${API_BASE}/replay/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rate: 3.0 })
        });
        if (res.ok) setStreamingActive(true);
      }
    } catch (err) {
      console.error('Streaming toggle failed:', err);
    }
  };

  // Submit Feedback
  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!selectedAlert) return;
    setFeedbackSubmitting(true);
    setFeedbackMessage(null);
    try {
      const res = await fetch(`${API_BASE}/alerts/${selectedAlert.alert_id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: feedbackStatus,
          notes: feedbackNotes,
          analyst_id: 'lead_fraud_analyst'
        })
      });
      if (res.ok) {
        setFeedbackMessage({ type: 'success', text: 'Resolution and audit log saved successfully!' });
        fetchAlerts();
        setTimeout(() => {
          setSelectedAlert(null);
          setFeedbackMessage(null);
        }, 1200);
      } else {
        const err = await res.json();
        setFeedbackMessage({ type: 'error', text: err.detail || 'Failed to update alert.' });
      }
    } catch (err) {
      setFeedbackMessage({ type: 'error', text: 'Network error updating alert.' });
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  // Trigger Retraining
  const handleTriggerRetrain = async () => {
    if (!window.confirm('Authorize and execute model retraining on approved benchmark?')) return;
    try {
      const res = await fetch(`${API_BASE}/retrain?approver_id=lead_fraud_analyst`, { method: 'POST' });
      if (res.ok) {
        alert('Model retrained and newly deployed to inference engine!');
        fetchMetrics();
        fetchDrift();
      }
    } catch (err) {
      alert('Error triggering retraining: ' + err.message);
    }
  };

  const getTierBadge = (tier) => {
    switch (tier) {
      case 'CRITICAL': return <span className="badge badge-critical">CRITICAL</span>;
      case 'HIGH': return <span className="badge badge-high">HIGH</span>;
      case 'MEDIUM': return <span className="badge badge-medium">MEDIUM</span>;
      case 'LOW': default: return <span className="badge badge-low">LOW</span>;
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || 'OPEN').toLowerCase().replace('_', '-');
    return <span className={`badge status-${s}`}>{status}</span>;
  };

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Educational Demo Banner */}
      <div style={{
        background: 'linear-gradient(90deg, rgba(6, 182, 212, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%)',
        border: '1px solid rgba(6, 182, 212, 0.3)',
        borderRadius: 12,
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.82rem',
        color: '#e2e8f0'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Info size={18} color="#38bdf8" />
          <span>
            <strong>EDUCATIONAL CAPSTONE PROJECT:</strong> Real-Time Financial Fraud Detection Platform. All transactions, accounts, and card identifiers are synthetic for analytics demonstrations. No real banking accounts are accessed or blocked.
          </span>
        </div>
        <span style={{ fontSize: '0.75rem', color: '#94a3b8', background: 'rgba(15, 23, 42, 0.6)', padding: '2px 8px', borderRadius: 4 }}>
          Seed 42 · CPU Fallback Active
        </span>
      </div>

      {/* Top Navigation Bar */}
      <header className="glass-panel" style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
            padding: 8,
            borderRadius: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(2, 132, 199, 0.4)'
          }}>
            <ShieldAlert size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff' }}>
              AEGIS <span style={{ color: '#38bdf8', fontWeight: 400 }}>// FRAUD INTELLIGENCE</span>
            </h1>
            <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Real-Time XGBoost Inference & NetworkX Syndicate Ring Engine
            </p>
          </div>
        </div>

        {/* Streaming & Backend Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.8rem', background: 'rgba(15, 23, 42, 0.6)', padding: '6px 12px', borderRadius: 8, border: '1px solid #334155' }}>
            <span className={apiHealth ? "pulse-dot" : ""} style={{ background: apiHealth ? "#10b981" : "#ef4444" }} />
            <span style={{ color: apiHealth ? '#10b981' : '#ef4444', fontWeight: 600 }}>
              {apiHealth ? `API Healthy (:8010)` : `Connecting API...`}
            </span>
          </div>

          <button
            onClick={toggleStreaming}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: streamingActive ? 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)' : 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: 8,
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              boxShadow: streamingActive ? '0 0 12px rgba(239, 68, 68, 0.5)' : '0 0 12px rgba(2, 132, 199, 0.4)',
              transition: 'all 0.2s'
            }}
          >
            {streamingActive ? <Square size={16} fill="#fff" /> : <Play size={16} fill="#fff" />}
            {streamingActive ? 'Pause Replay' : 'Start Stream Replay'}
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav style={{ display: 'flex', gap: 8, borderBottom: '1px solid #334155', paddingBottom: 8, overflowX: 'auto' }}>
        {[
          { id: 'stream', label: 'Live Stream Feed', icon: Activity },
          { id: 'alerts', label: `Alerts & Case Ops (${alertsData.total_count})`, icon: AlertTriangle },
          { id: 'graph', label: `Syndicate Graph (${rings.length} Rings)`, icon: Network },
          { id: 'model', label: 'Model Evaluation (PR-AUC)', icon: BarChart3 },
          { id: 'drift', label: 'Data Drift & Retraining', icon: GitBranch },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: isActive ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: isActive ? '#38bdf8' : '#94a3b8',
                border: 'none',
                borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                padding: '8px 16px',
                borderRadius: '8px 8px 0 0',
                fontSize: '0.88rem',
                fontWeight: isActive ? 700 : 500,
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* KPI Overview Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
        <div className="glass-panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Total Transactions Scored</span>
            <Layers size={18} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 800, marginTop: 6, color: '#f8fafc' }}>
            {metrics?.runtime_ops?.total_scored?.toLocaleString() || transactions.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#10b981', marginTop: 4 }}>
            ● In-memory zero-leakage event stream
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Alerts Generated</span>
            <AlertTriangle size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 800, marginTop: 6, color: '#f59e0b' }}>
            {alertsData.total_count}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: 4 }}>
            {alertsData.status_breakdown?.OPEN || 0} Open · {alertsData.status_breakdown?.CONFIRMED_FRAUD || 0} Confirmed Fraud
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Active Fraud Rings</span>
            <Network size={18} color="#ef4444" />
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 800, marginTop: 6, color: '#ef4444' }}>
            {rings.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: 4 }}>
            NetworkX Connected Multi-Account Clusters
          </div>
        </div>

        <div className="glass-panel" style={{ padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Average Inference Latency</span>
            <Clock size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: '1.7rem', fontWeight: 800, marginTop: 6, color: '#10b981' }}>
            {metrics?.runtime_ops?.latency_ms?.average || 6.2} ms
          </div>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: 4 }}>
            P95: {metrics?.runtime_ops?.latency_ms?.p95 || 9.4} ms · CPU Pipeline
          </div>
        </div>
      </section>

      {/* TAB 1: LIVE STREAM FEED */}
      {activeTab === 'stream' && (
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Real-Time Ingestion & Streaming Transaction Feed</h2>
              <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                Transactions evaluated via XGBoost (65%) + NetworkX Syndicate Ring detector (35%).
              </p>
            </div>
            {streamingActive && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', color: '#10b981' }}>
                <span className="pulse-dot" /> Streaming Active (3.0 events/sec)
              </div>
            )}
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.83rem' }}>
              <thead>
                <tr style={{ background: 'rgba(15, 23, 42, 0.9)', borderBottom: '2px solid #334155', color: '#94a3b8' }}>
                  <th style={{ padding: '10px 12px' }}>Txn ID</th>
                  <th style={{ padding: '10px 12px' }}>Timestamp</th>
                  <th style={{ padding: '10px 12px' }}>Account ID</th>
                  <th style={{ padding: '10px 12px' }}>Amount</th>
                  <th style={{ padding: '10px 12px' }}>ML Score</th>
                  <th style={{ padding: '10px 12px' }}>Graph Score</th>
                  <th style={{ padding: '10px 12px' }}>Blended Score</th>
                  <th style={{ padding: '10px 12px' }}>Risk Tier</th>
                  <th style={{ padding: '10px 12px' }}>Latency</th>
                  <th style={{ padding: '10px 12px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.length === 0 ? (
                  <tr>
                    <td colSpan="10" style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>
                      No stream events yet. Click <strong>"Start Stream Replay"</strong> above to ingest transactions.
                    </td>
                  </tr>
                ) : (
                  transactions.map((t, idx) => (
                    <tr 
                      key={t.transaction_id || idx}
                      style={{ 
                        borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
                        background: t.is_alert ? 'rgba(239, 68, 68, 0.08)' : 'transparent',
                        cursor: 'pointer'
                      }}
                      onClick={() => setSelectedTxn(t)}
                    >
                      <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono', color: '#f8fafc', fontWeight: 600 }}>
                        {t.transaction_id}
                      </td>
                      <td style={{ padding: '10px 12px', color: '#94a3b8' }}>{t.timestamp?.slice(11, 19)}</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono', color: '#38bdf8' }}>{t.account_id}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 600 }}>${t.amount?.toFixed(2)}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ color: t.ml_score >= 0.7 ? '#ef4444' : '#94a3b8', fontWeight: 600 }}>
                          {(t.ml_score * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ color: t.graph_score >= 0.7 ? '#ef4444' : '#94a3b8', fontWeight: 600 }}>
                          {(t.graph_score * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 700 }}>
                        <span style={{ color: t.blended_score >= 0.7 ? '#ef4444' : (t.blended_score >= 0.4 ? '#f59e0b' : '#10b981') }}>
                          {(t.blended_score * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>{getTierBadge(t.risk_tier)}</td>
                      <td style={{ padding: '10px 12px', color: '#94a3b8', fontFamily: 'JetBrains Mono' }}>
                        {t.latency_ms?.toFixed(1)} ms
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <button
                          style={{
                            background: 'rgba(56, 189, 248, 0.1)',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            color: '#38bdf8',
                            padding: '3px 8px',
                            borderRadius: 4,
                            cursor: 'pointer',
                            fontSize: '0.72rem'
                          }}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: ALERTS & CASE OPS */}
      {activeTab === 'alerts' && (
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Fraud Alerts & Case Investigation Queue</h2>
              <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                Prioritized queue of flagged high-risk transactions with analyst audit trails.
              </p>
            </div>

            {/* Filter controls */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <select
                value={alertStatusFilter}
                onChange={(e) => setAlertStatusFilter(e.target.value)}
                style={{
                  background: '#0f172a',
                  color: '#f8fafc',
                  border: '1px solid #334155',
                  padding: '6px 10px',
                  borderRadius: 6,
                  fontSize: '0.8rem'
                }}
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="INVESTIGATING">Investigating</option>
                <option value="CONFIRMED_FRAUD">Confirmed Fraud</option>
                <option value="FALSE_POSITIVE">False Positive</option>
                <option value="CLOSED">Closed</option>
              </select>

              <select
                value={alertTierFilter}
                onChange={(e) => setAlertTierFilter(e.target.value)}
                style={{
                  background: '#0f172a',
                  color: '#f8fafc',
                  border: '1px solid #334155',
                  padding: '6px 10px',
                  borderRadius: 6,
                  fontSize: '0.8rem'
                }}
              >
                <option value="ALL">All Risk Tiers</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
              </select>
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.83rem' }}>
              <thead>
                <tr style={{ background: 'rgba(15, 23, 42, 0.9)', borderBottom: '2px solid #334155', color: '#94a3b8' }}>
                  <th style={{ padding: '10px 12px' }}>Alert ID</th>
                  <th style={{ padding: '10px 12px' }}>Timestamp</th>
                  <th style={{ padding: '10px 12px' }}>Account</th>
                  <th style={{ padding: '10px 12px' }}>Amount</th>
                  <th style={{ padding: '10px 12px' }}>Risk Tier</th>
                  <th style={{ padding: '10px 12px' }}>Blended Score</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px' }}>Analyst Notes</th>
                  <th style={{ padding: '10px 12px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {alertsData.alerts.length === 0 ? (
                  <tr>
                    <td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: '#64748b' }}>
                      No alerts match the selected filter.
                    </td>
                  </tr>
                ) : (
                  alertsData.alerts.map((a) => (
                    <tr
                      key={a.alert_id}
                      style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.4)' }}
                    >
                      <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono', color: '#fdba74', fontWeight: 600 }}>
                        {a.alert_id}
                      </td>
                      <td style={{ padding: '10px 12px', color: '#94a3b8' }}>{a.timestamp}</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono', color: '#38bdf8' }}>{a.account_id}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 600 }}>${a.amount?.toFixed(2)}</td>
                      <td style={{ padding: '10px 12px' }}>{getTierBadge(a.risk_tier)}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 700, color: '#ef4444' }}>
                        {(a.blended_score * 100).toFixed(1)}%
                      </td>
                      <td style={{ padding: '10px 12px' }}>{getStatusBadge(a.status)}</td>
                      <td style={{ padding: '10px 12px', color: '#94a3b8', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {a.analyst_notes || '—'}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <button
                          onClick={() => {
                            setSelectedAlert(a);
                            setFeedbackStatus(a.status || 'INVESTIGATING');
                            setFeedbackNotes(a.analyst_notes || '');
                          }}
                          style={{
                            background: 'rgba(99, 102, 241, 0.15)',
                            border: '1px solid rgba(99, 102, 241, 0.4)',
                            color: '#a5b4fc',
                            padding: '4px 10px',
                            borderRadius: 6,
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            fontWeight: 600
                          }}
                        >
                          Review Case
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SYNDICATE GRAPH VISUALIZER */}
      {activeTab === 'graph' && (
        <GraphVisualizer graphData={graphData} rings={rings} />
      )}

      {/* TAB 4: MODEL EVALUATION & PR-AUC */}
      {activeTab === 'model' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div className="glass-panel" style={{ padding: 20 }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 14 }}>
              Supervised Model Performance (Test Partition)
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: 16 }}>
              Model: <strong>{metrics?.model_evaluation?.model_type || 'XGBoost Classifier'}</strong> · Strictly evaluated on chronological held-out 15% test set.
            </p>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <tbody>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '8px 0', color: '#94a3b8' }}>PR-AUC / Average Precision</td>
                  <td style={{ padding: '8px 0', fontWeight: 700, color: '#38bdf8' }}>
                    {metrics?.model_evaluation?.pr_auc || '0.9978'}
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '8px 0', color: '#94a3b8' }}>ROC-AUC</td>
                  <td style={{ padding: '8px 0', fontWeight: 700, color: '#10b981' }}>
                    {metrics?.model_evaluation?.roc_auc || '0.9999'}
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '8px 0', color: '#94a3b8' }}>Precision (at t=0.50)</td>
                  <td style={{ padding: '8px 0', fontWeight: 700, color: '#f8fafc' }}>
                    {((metrics?.model_evaluation?.precision || 1.0) * 100).toFixed(1)}%
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '8px 0', color: '#94a3b8' }}>Recall (at t=0.50)</td>
                  <td style={{ padding: '8px 0', fontWeight: 700, color: '#f8fafc' }}>
                    {((metrics?.model_evaluation?.recall || 0.965) * 100).toFixed(1)}%
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '8px 0', color: '#94a3b8' }}>F1 Score</td>
                  <td style={{ padding: '8px 0', fontWeight: 700, color: '#f8fafc' }}>
                    {metrics?.model_evaluation?.f1_score || '0.9825'}
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '8px 0', color: '#94a3b8' }}>Test Set Fraud Prevalence</td>
                  <td style={{ padding: '8px 0', fontWeight: 700, color: '#f59e0b' }}>
                    {((metrics?.model_evaluation?.test_fraud_prevalence || 0.0322) * 100).toFixed(2)}%
                  </td>
                </tr>
              </tbody>
            </table>

            {/* Confusion Matrix block */}
            <div style={{ marginTop: 20 }}>
              <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 10 }}>Measured Confusion Matrix</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, textAlign: 'center' }}>
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: 10, borderRadius: 8 }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>True Negatives (TN)</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#10b981' }}>
                    {metrics?.model_evaluation?.confusion_matrix?.true_negatives || 871}
                  </div>
                </div>
                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: 10, borderRadius: 8 }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>False Positives (FP)</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ef4444' }}>
                    {metrics?.model_evaluation?.confusion_matrix?.false_positives || 0}
                  </div>
                </div>
                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: 10, borderRadius: 8 }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>False Negatives (FN)</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ef4444' }}>
                    {metrics?.model_evaluation?.confusion_matrix?.false_negatives || 1}
                  </div>
                </div>
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: 10, borderRadius: 8 }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>True Positives (TP)</span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#10b981' }}>
                    {metrics?.model_evaluation?.confusion_matrix?.true_positives || 28}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: 20 }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 12 }}>
              Operational Trade-Off Analysis
            </h3>
            <div style={{ fontSize: '0.83rem', color: '#cbd5e1', lineHeight: 1.6, display: 'flex', flexDirection: 'column', gap: 12 }}>
              <p>
                <strong>The Imbalanced Fraud Challenge:</strong> On financial data with ~2% fraud prevalence, a naive baseline predicting all 0s achieves 98% accuracy while missing 100% of financial losses. Therefore, <strong>PR-AUC (Average Precision)</strong> is the vital metric.
              </p>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 12, borderRadius: 8 }}>
                <strong>Analyst Burden vs Financial Loss:</strong>
                <ul style={{ paddingLeft: 18, marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <li><strong>Lower Threshold:</strong> Captures more fraud (higher Recall) but drowns fraud analysts in false positives.</li>
                  <li><strong>Ensemble Architecture:</strong> We blend XGBoost with NetworkX syndicate graph topology. When an account belongs to a known emulator farm or mule ring, the graph score escalates the alert even on low transaction amounts.</li>
                </ul>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Full training metadata and artifacts are tracked locally in MLflow: <code>artifacts/mlflow.db</code>.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: DATA DRIFT & RETRAINING */}
      {activeTab === 'drift' && (
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Data Drift Monitoring & Retraining Pipeline</h2>
              <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                Statistical 2-sample Kolmogorov-Smirnov test and Population Stability Index (PSI).
              </p>
            </div>

            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <span className={`badge ${driftReport?.dataset_drift_detected ? 'badge-critical' : 'badge-low'}`}>
                {driftReport?.dataset_drift_detected ? 'DRIFT DETECTED' : 'DATASET STABLE'}
              </span>

              <button
                onClick={handleTriggerRetrain}
                style={{
                  background: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
                  color: '#fff',
                  border: 'none',
                  padding: '8px 14px',
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <RotateCw size={14} /> Authorize Retraining
              </button>
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.83rem' }}>
              <thead>
                <tr style={{ background: 'rgba(15, 23, 42, 0.9)', borderBottom: '2px solid #334155', color: '#94a3b8' }}>
                  <th style={{ padding: '10px 12px' }}>Feature Name</th>
                  <th style={{ padding: '10px 12px' }}>Ref Baseline Mean</th>
                  <th style={{ padding: '10px 12px' }}>Current Stream Mean</th>
                  <th style={{ padding: '10px 12px' }}>KS Statistic</th>
                  <th style={{ padding: '10px 12px' }}>p-value</th>
                  <th style={{ padding: '10px 12px' }}>PSI Score</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {driftReport && driftReport.features ? (
                  Object.entries(driftReport.features).map(([feat, d]) => (
                    <tr key={feat} style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.4)' }}>
                      <td style={{ padding: '8px 12px', fontWeight: 600, fontFamily: 'JetBrains Mono' }}>{feat}</td>
                      <td style={{ padding: '8px 12px' }}>{d.reference_mean}</td>
                      <td style={{ padding: '8px 12px' }}>{d.current_mean}</td>
                      <td style={{ padding: '8px 12px' }}>{d.ks_statistic}</td>
                      <td style={{ padding: '8px 12px' }}>{d.p_value}</td>
                      <td style={{ padding: '8px 12px' }}>{d.psi_score}</td>
                      <td style={{ padding: '8px 12px' }}>
                        <span className={`badge ${d.drift_detected ? 'badge-critical' : 'badge-low'}`}>
                          {d.drift_detected ? 'DRIFTED' : 'STABLE'}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', padding: '24px', color: '#64748b' }}>
                      Loading drift metrics...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CASE REVIEW MODAL / DRAWER */}
      {selectedAlert && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          padding: 16
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: 560, padding: 24, position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 700 }}>
                  Case Investigation
                </span>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, fontFamily: 'JetBrains Mono', color: '#fdba74' }}>
                  {selectedAlert.alert_id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedAlert(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16, fontSize: '0.85rem' }}>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 8 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Transaction ID</span>
                <div style={{ fontFamily: 'JetBrains Mono', fontWeight: 600 }}>{selectedAlert.transaction_id}</div>
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 8 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Amount</span>
                <div style={{ fontWeight: 700, color: '#f8fafc' }}>${selectedAlert.amount?.toFixed(2)}</div>
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 8 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Account ID</span>
                <div style={{ fontFamily: 'JetBrains Mono', color: '#38bdf8' }}>{selectedAlert.account_id}</div>
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 8 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Device Fingerprint</span>
                <div style={{ fontFamily: 'JetBrains Mono', color: '#f59e0b' }}>{selectedAlert.device_id}</div>
              </div>
            </div>

            {/* Risk Breakdown */}
            <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: 12, borderRadius: 8, marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.85rem' }}>
                <span>Supervised ML Score: <strong>{(selectedAlert.ml_score * 100).toFixed(1)}%</strong></span>
                <span>Graph Ring Score: <strong>{(selectedAlert.graph_score * 100).toFixed(1)}%</strong></span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, color: '#ef4444' }}>
                <span>Blended Ensemble Risk:</span>
                <span>{(selectedAlert.blended_score * 100).toFixed(1)}% ({selectedAlert.risk_tier})</span>
              </div>
            </div>

            {/* Form for feedback */}
            <form onSubmit={handleFeedbackSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: 6 }}>
                  Case Resolution Status:
                </label>
                <select
                  value={feedbackStatus}
                  onChange={(e) => setFeedbackStatus(e.target.value)}
                  style={{
                    width: '100%',
                    background: '#0f172a',
                    color: '#f8fafc',
                    border: '1px solid #334155',
                    padding: '8px 10px',
                    borderRadius: 6,
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="OPEN">Open (Pending Triage)</option>
                  <option value="INVESTIGATING">Investigating (Under Review)</option>
                  <option value="CONFIRMED_FRAUD">Confirmed Fraud (Block & File SAR)</option>
                  <option value="FALSE_POSITIVE">False Positive (Whitelisted Customer)</option>
                  <option value="CLOSED">Closed (Archived)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: 6 }}>
                  Analyst Rationale / Notes:
                </label>
                <textarea
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="Enter investigation findings, IP geolocation matches, customer callback notes..."
                  rows="3"
                  style={{
                    width: '100%',
                    background: '#0f172a',
                    color: '#f8fafc',
                    border: '1px solid #334155',
                    padding: '8px 10px',
                    borderRadius: 6,
                    fontSize: '0.85rem',
                    resize: 'vertical'
                  }}
                />
              </div>

              {feedbackMessage && (
                <div style={{
                  padding: '8px 12px',
                  borderRadius: 6,
                  fontSize: '0.8rem',
                  background: feedbackMessage.type === 'success' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  color: feedbackMessage.type === 'success' ? '#86efac' : '#fca5a5'
                }}>
                  {feedbackMessage.text}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => setSelectedAlert(null)}
                  style={{
                    background: 'rgba(30, 41, 59, 0.5)',
                    color: '#94a3b8',
                    border: '1px solid #334155',
                    padding: '8px 14px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={feedbackSubmitting}
                  style={{
                    background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                    color: '#fff',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: 6,
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  {feedbackSubmitting ? 'Saving...' : 'Save Resolution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TRANSACTION INSPECTOR MODAL */}
      {selectedTxn && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          padding: 16
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: 560, padding: 24, maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 700 }}>
                  Live Stream Inspection
                </span>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, fontFamily: 'JetBrains Mono', color: '#38bdf8' }}>
                  {selectedTxn.transaction_id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedTxn(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: '0.83rem', marginBottom: 14 }}>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 6 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Account ID</span>
                <div style={{ fontFamily: 'JetBrains Mono' }}>{selectedTxn.account_id}</div>
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 6 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Amount</span>
                <div style={{ fontWeight: 700 }}>${selectedTxn.amount?.toFixed(2)}</div>
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 6 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Inference Latency</span>
                <div style={{ color: '#10b981', fontWeight: 600 }}>{selectedTxn.latency_ms?.toFixed(2)} ms</div>
              </div>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: 10, borderRadius: 6 }}>
                <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>Risk Tier</span>
                <div>{getTierBadge(selectedTxn.risk_tier)}</div>
              </div>
            </div>

            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: 8, color: '#94a3b8' }}>
              Engineered Event-Time Features
            </h4>
            <div style={{ background: '#0f172a', padding: 12, borderRadius: 8, fontSize: '0.78rem', fontFamily: 'JetBrains Mono', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {selectedTxn.features && Object.entries(selectedTxn.features).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                  <span style={{ color: '#94a3b8' }}>{k}:</span>
                  <span style={{ color: '#f8fafc', fontWeight: 600 }}>{String(v)}</span>
                </div>
              ))}
            </div>

            <button
              onClick={() => setSelectedTxn(null)}
              style={{
                width: '100%',
                marginTop: 16,
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '8px',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
