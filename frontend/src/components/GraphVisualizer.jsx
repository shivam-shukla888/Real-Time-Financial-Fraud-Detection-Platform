import React, { useState, useMemo } from 'react';
import { Network, ShieldAlert, Cpu, UserCheck, Store, MapPin } from 'lucide-react';

export default function GraphVisualizer({ graphData, rings = [] }) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [filterType, setFilterType] = useState('ALL');

  const width = 800;
  const height = 480;

  // Calculate deterministic layout coordinates for nodes
  const layoutNodes = useMemo(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return [];

    const nodes = [...graphData.nodes];
    const total = nodes.length;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.38;

    return nodes.map((n, i) => {
      // Group ring nodes near cluster centers
      let angle = (i / total) * 2 * Math.PI;
      let r = radius;

      if (n.type === 'device') {
        r = radius * 0.55;
      } else if (n.type === 'merchant') {
        r = radius * 0.85;
      }

      // Add slight jitter based on hash of id
      const hash = n.id.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
      const jitterX = (hash % 20) - 10;
      const jitterY = ((hash * 7) % 20) - 10;

      return {
        ...n,
        x: centerX + r * Math.cos(angle) + jitterX,
        y: centerY + r * Math.sin(angle) + jitterY
      };
    });
  }, [graphData]);

  const nodeMap = useMemo(() => {
    const map = {};
    layoutNodes.forEach(n => { map[n.id] = n; });
    return map;
  }, [layoutNodes]);

  const filteredNodes = useMemo(() => {
    if (filterType === 'ALL') return layoutNodes;
    return layoutNodes.filter(n => n.type === filterType.toLowerCase());
  }, [layoutNodes, filterType]);

  const nodeColor = (node) => {
    if (node.id.includes('RING') || node.id.includes('MULE') || node.id.includes('EMULATOR')) {
      return '#ef4444'; // Red for syndicate ring
    }
    switch (node.type) {
      case 'account': return '#38bdf8'; // Sky blue
      case 'device': return '#f59e0b'; // Amber
      case 'merchant': return '#10b981'; // Emerald
      case 'location': return '#818cf8'; // Indigo
      default: return '#94a3b8';
    }
  };

  const nodeIcon = (type) => {
    switch (type) {
      case 'account': return <UserCheck size={14} color="#38bdf8" />;
      case 'device': return <Cpu size={14} color="#f59e0b" />;
      case 'merchant': return <Store size={14} color="#10b981" />;
      case 'location': return <MapPin size={14} color="#818cf8" />;
      default: return <Network size={14} color="#94a3b8" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Visualizer Header & Filter Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Network size={20} color="#06b6d4" />
            Entity Relationship & Fraud Ring Visualizer
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Interactive NetworkX bipartite projection showing Account ↔ Device ↔ Merchant connections.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 6 }}>
          {['ALL', 'ACCOUNT', 'DEVICE', 'MERCHANT'].map(t => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              style={{
                background: filterType === t ? 'rgba(6, 182, 212, 0.25)' : 'rgba(30, 41, 59, 0.5)',
                color: filterType === t ? '#22d3ee' : '#94a3b8',
                border: `1px solid ${filterType === t ? '#06b6d4' : '#334155'}`,
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Canvas & Inspector Card */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedNode ? '1fr 280px' : '1fr', gap: 16 }}>
        <div 
          className="glass-panel" 
          style={{ position: 'relative', overflow: 'hidden', minHeight: 480, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 8 }}
        >
          {layoutNodes.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <Network size={40} style={{ opacity: 0.4, margin: '0 auto 12px' }} />
              <p>No entity graph data loaded. Trigger stream replay to view live entities.</p>
            </div>
          ) : (
            <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '100%', maxHeight: 500 }}>
              {/* Edges */}
              {graphData.edges && graphData.edges.map((e, idx) => {
                const source = nodeMap[e.source];
                const target = nodeMap[e.target];
                if (!source || !target) return null;
                const isSelected = selectedNode && (selectedNode.id === e.source || selectedNode.id === e.target);
                const isHighRisk = e.source.includes('RING') || e.target.includes('RING');
                return (
                  <line
                    key={idx}
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke={isSelected ? '#38bdf8' : (isHighRisk ? 'rgba(239, 68, 68, 0.6)' : 'rgba(100, 116, 139, 0.25)')}
                    strokeWidth={isSelected ? 2.5 : (isHighRisk ? 1.8 : 1.0)}
                    strokeDasharray={isHighRisk ? '4,2' : 'none'}
                  />
                );
              })}

              {/* Nodes */}
              {filteredNodes.map((n) => {
                const isSelected = selectedNode && selectedNode.id === n.id;
                const col = nodeColor(n);
                const radius = n.type === 'device' ? 12 : (n.type === 'merchant' ? 10 : 8);

                return (
                  <g 
                    key={n.id} 
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedNode(n)}
                  >
                    <circle
                      cx={n.x}
                      cy={n.y}
                      r={radius + (isSelected ? 4 : 0)}
                      fill={col}
                      fillOpacity={0.85}
                      stroke={isSelected ? '#fff' : 'rgba(15, 23, 42, 0.8)'}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                    />
                    <text
                      x={n.x}
                      y={n.y + radius + 11}
                      fill={isSelected ? '#fff' : '#94a3b8'}
                      fontSize="9"
                      fontFamily="JetBrains Mono, monospace"
                      textAnchor="middle"
                      fontWeight={isSelected ? '700' : '500'}
                    >
                      {n.label.length > 14 ? n.label.slice(0, 12) + '..' : n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}

          {/* Legend Overlay */}
          <div style={{
            position: 'absolute',
            bottom: 12,
            left: 12,
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid #334155',
            borderRadius: 8,
            padding: '8px 12px',
            fontSize: '0.75rem',
            display: 'flex',
            gap: 12,
            flexWrap: 'wrap'
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#38bdf8' }} /> Account
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }} /> Device
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} /> Merchant
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444' }} /> Ring / Syndicate
            </span>
          </div>
        </div>

        {/* Selected Node Inspector Drawer */}
        {selectedNode && (
          <div className="glass-panel" style={{ padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {nodeIcon(selectedNode.type)}
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
                  {selectedNode.type}
                </span>
              </div>
              <button 
                onClick={() => setSelectedNode(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1rem' }}
              >
                ✕
              </button>
            </div>

            <h4 style={{ fontSize: '1rem', fontWeight: 700, fontFamily: 'JetBrains Mono', wordBreak: 'break-all', marginBottom: 8 }}>
              {selectedNode.label}
            </h4>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'grid', gap: 8, marginTop: 12 }}>
              <div style={{ background: 'rgba(30, 41, 59, 0.4)', padding: 8, borderRadius: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Graph Degree: </span>
                <strong style={{ color: '#fff' }}>{selectedNode.degree} connections</strong>
              </div>

              {selectedNode.id.includes('RING') && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: 8, borderRadius: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#fca5a5', fontWeight: 700 }}>
                    <ShieldAlert size={14} /> Syndicate Ring Detected
                  </div>
                  <p style={{ fontSize: '0.75rem', color: '#fecaca', marginTop: 4 }}>
                    Multi-account shared device funneling suspicious transfers.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Identified Syndicate Rings Summary Cards */}
      {rings.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 12 }}>
            IDENTIFIED FRAUD RINGS & BOT EMULATOR FARMS ({rings.length})
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
            {rings.map((r) => (
              <div 
                key={r.ring_id} 
                className="glass-panel" 
                style={{ 
                  padding: 14, 
                  borderLeft: `4px solid ${r.risk_score >= 0.8 ? '#ef4444' : '#f59e0b'}` 
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '0.9rem', color: '#f8fafc' }}>{r.title}</strong>
                  <span className="badge badge-critical">Risk {(r.risk_score * 100).toFixed(0)}%</span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 8, display: 'flex', gap: 16 }}>
                  <span>Accounts: <strong style={{ color: '#fff' }}>{r.accounts_count}</strong></span>
                  <span>Devices: <strong style={{ color: '#fff' }}>{r.devices_count}</strong></span>
                  <span>Merchants: <strong style={{ color: '#fff' }}>{r.merchants_count}</strong></span>
                </div>
                <div style={{ marginTop: 8, fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'JetBrains Mono' }}>
                  Linked: {r.accounts.slice(0, 3).join(', ')}...
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
