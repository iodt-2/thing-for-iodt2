/**
 * TwinGraphView — Tenant graph visualization with ReactFlow v12 (@xyflow/react)
 *
 * Kritik: Custom node'lar <Handle type="source"> ve <Handle type="target">
 * içermeli. Aksi halde edge'ler render edilmez (no connection points).
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  MarkerType,
  BackgroundVariant,
  Panel,
  Position,
  Handle,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import Dagre from '@dagrejs/dagre'

import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { Cpu, Radio, Layers, RefreshCw, List, Info, X, Network, GitBranch, MoveHorizontal, MoveVertical } from 'lucide-react'
import TwinService from '@/services/twinService'
import useTenantStore from '@/store/useTenantStore'
import useSidebarStore from '@/store/useSidebarStore'

// ─── Constants ────────────────────────────────────────────────────────────────

const REL_COLORS = {
  feeds:     '#f59e0b',
  controls:  '#ef4444',
  contains:  '#8b5cf6',
  monitors:  '#10b981',
  dependsOn: '#6366f1',
}

const INVERSE_TYPES = new Set([
  'isFedBy', 'isControlledBy', 'isContainedIn', 'isMonitoredBy', 'isDependedOnBy',
])

const TYPE_META = {
  atomic:    { label: 'Atomic Twin',    Icon: Radio,  lightBg: '#ecfdf5', lightBorder: '#10b981', lightText: '#065f46', lightBadge: '#d1fae5', darkBg: '#064e3b', darkBorder: '#34d399', darkText: '#6ee7b7', darkBadge: '#065f46', hex: '#10b981' },
  composite: { label: 'Composite Twin', Icon: Cpu,    lightBg: '#eff6ff', lightBorder: '#3b82f6', lightText: '#1e40af', lightBadge: '#dbeafe', darkBg: '#1e3a5f', darkBorder: '#60a5fa', darkText: '#93c5fd', darkBadge: '#1e40af', hex: '#3b82f6' },
  system:    { label: 'System Twin',    Icon: Layers, lightBg: '#f5f3ff', lightBorder: '#8b5cf6', lightText: '#4c1d95', lightBadge: '#ede9fe', darkBg: '#2e1065', darkBorder: '#a78bfa', darkText: '#c4b5fd', darkBadge: '#4c1d95', hex: '#8b5cf6' },
}
const UNKNOWN_META = {
  label: 'Unknown', Icon: Cpu,
  lightBg: '#f9fafb', lightBorder: '#9ca3af', lightText: '#374151', lightBadge: '#f3f4f6',
  darkBg: '#1e293b', darkBorder: '#475569', darkText: '#94a3b8', darkBadge: '#334155',
  hex: '#9ca3af',
}

// ─── Theme hook — dark class'ını DOM'da izler, tema değişince re-render ───────
function useIsDark() {
  const [isDark, setIsDark] = useState(
    () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  )
  useEffect(() => {
    const el = document.documentElement
    const update = () => setIsDark(el.classList.contains('dark'))
    update()
    const mo = new MutationObserver(update)
    mo.observe(el, { attributes: true, attributeFilter: ['class'] })
    return () => mo.disconnect()
  }, [])
  return isDark
}

// ─── Custom node ──────────────────────────────────────────────────────────────
// KRİTİK: Handle'lar edge'lerin bağlandığı noktalardır. Olmazsa edge render edilmez.
function TwinNode({ data, selected }) {
  const meta   = TYPE_META[data.thingType] || UNKNOWN_META
  const { Icon } = meta
  const isDark = data.isDark
  const bg     = isDark ? meta.darkBg     : meta.lightBg
  const border = isDark ? meta.darkBorder : meta.lightBorder
  const text   = isDark ? meta.darkText   : meta.lightText
  const badge  = isDark ? meta.darkBadge  : meta.lightBadge

  const handleStyle = {
    width: 9,
    height: 9,
    background: border,
    border: `2px solid ${isDark ? '#0f172a' : '#ffffff'}`,
    boxShadow: `0 0 0 2px ${border}33`,
  }

  const glow = selected
    ? `0 0 0 3px ${border}55, 0 8px 24px ${border}44`
    : isDark
      ? '0 2px 12px rgba(0,0,0,0.55)'
      : '0 2px 10px rgba(0,0,0,0.12)'

  return (
    <div
      className="twin-node"
      style={{
        background: `linear-gradient(135deg, ${bg} 0%, ${isDark ? meta.darkBadge : meta.lightBadge} 100%)`,
        border: `2px solid ${border}`,
        borderRadius: 14,
        padding: '11px 15px',
        minWidth: 170,
        maxWidth: 230,
        boxShadow: glow,
        fontFamily: 'inherit',
        userSelect: 'none',
        cursor: 'pointer',
        position: 'relative',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease',
        transform: selected ? 'translateY(-1px) scale(1.02)' : 'none',
      }}>
      {/* 4 tarafta Handle — Dagre yönüne göre xyflow doğru olanı kullanır */}
      <Handle type="target" position={Position.Left}   id="tl" style={handleStyle} isConnectable={false} />
      <Handle type="target" position={Position.Top}    id="tt" style={handleStyle} isConnectable={false} />
      <Handle type="source" position={Position.Right}  id="sr" style={handleStyle} isConnectable={false} />
      <Handle type="source" position={Position.Bottom} id="sb" style={handleStyle} isConnectable={false} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 22,
          height: 22,
          borderRadius: 6,
          background: isDark ? 'rgba(0,0,0,0.25)' : 'rgba(255,255,255,0.6)',
          flexShrink: 0,
        }}>
          <Icon size={13} color={border} />
        </span>
        <span style={{ fontSize: 12.5, fontWeight: 700, color: text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', letterSpacing: 0.2 }}>
          {data.label}
        </span>
      </div>
      {data.description && (
        <p style={{ fontSize: 10, color: text, opacity: 0.7, margin: '0 0 6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
           title={data.description}>
          {data.description}
        </p>
      )}
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        background: isDark ? 'rgba(0,0,0,0.28)' : 'rgba(255,255,255,0.55)',
        color: text,
        fontSize: 9.5,
        fontWeight: 700,
        padding: '2px 9px',
        borderRadius: 99,
        border: `1px solid ${border}44`,
      }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: border, display: 'inline-block' }} />
        {meta.label}
      </span>
    </div>
  )
}

// KRİTİK: nodeTypes modül seviyesinde sabit — her render'da yeni obje oluşturulmamalı
const NODE_TYPES = { twinNode: TwinNode }

// ─── Layout ────────────────────────────────────────────────────────────────────
// Dagre hiyerarşik auto-layout. rankdir: 'LR' (soldan sağa) veya 'TB' (üstten alta).
// Her node'un "targetPosition" ve "sourcePosition"'unu rankdir'e göre ayarlar,
// böylece Handle'lar edge'in geldiği/gittiği kenara konumlanır.
const NODE_W = 210
const NODE_H = 80

function computeLayout(rfNodes, rfEdges, direction = 'LR') {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir:   direction,
    nodesep:   direction === 'LR' ? 40 : 60,   // aynı rank içindeki node'lar arası
    ranksep:   direction === 'LR' ? 120 : 90,  // rank'lar arası mesafe
    marginx:   30,
    marginy:   30,
  })

  rfNodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  rfEdges.forEach((e) => g.setEdge(e.source, e.target))

  Dagre.layout(g)

  const isHorizontal = direction === 'LR'
  return rfNodes.map((n) => {
    const p = g.node(n.id)
    return {
      ...n,
      // Dagre merkez-koordinat verir; xyflow sol-üst köşe bekler
      position:       { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 },
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
    }
  })
}

// ─── Edge builder ──────────────────────────────────────────────────────────────
function buildEdges(rawEdges, nodeIdSet, isDark) {
  const seen = new Set()
  const out  = []
  rawEdges.forEach((e) => {
    const src = (e.sourceName || '').trim()
    const tgt = (e.targetName || '').trim()
    if (!src || !tgt) return
    if (INVERSE_TYPES.has(e.relType)) return
    // Güvenlik: edge hem source hem target node listesinde olmalı
    if (!nodeIdSet.has(src) || !nodeIdSet.has(tgt)) return

    const key = `${src}||${tgt}||${e.relName}`
    if (seen.has(key)) return
    seen.add(key)

    const color    = REL_COLORS[e.relType] || '#94a3b8'
    const inactive = e.status === 'Inactive'

    out.push({
      id:       `e-${src}-${e.relName || 'rel'}-${tgt}`,
      source:   src,
      target:   tgt,
      type:     'smoothstep',
      label:    e.relType || e.relName || '',
      animated: !inactive && (e.relType === 'feeds' || e.relType === 'monitors'),
      style: {
        stroke:          inactive ? '#94a3b8' : color,
        strokeWidth:     2.5,
        strokeDasharray: inactive ? '6 3' : undefined,
      },
      labelStyle: {
        fontSize: 10,
        fontWeight: 700,
        fill: isDark ? '#e2e8f0' : color,
      },
      labelBgStyle: {
        fill:        isDark ? '#1e293b' : '#ffffff',
        fillOpacity: 0.93,
      },
      labelBgPadding:      [4, 3],
      labelBgBorderRadius: 4,
      markerEnd: {
        type:   MarkerType.ArrowClosed,
        color:  inactive ? '#94a3b8' : color,
        width:  18,
        height: 18,
      },
    })
  })
  return out
}

// ─── Inner flow component (ReactFlowProvider içinde olmalı) ────────────────────
function FlowCanvas({ graphData, isDark, direction, onNodeSelect, C }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [isInteractive, setIsInteractive] = useState(true)

  // Node ve edge'leri graphData'dan atomik olarak üret
  useEffect(() => {
    if (!graphData) {
      setNodes([])
      setEdges([])
      return
    }
    const rawNodes = graphData.nodes || []
    const rfNodes = rawNodes.map((n) => ({
      id:       n.name,
      type:     'twinNode',
      data: {
        label:       n.name,
        description: n.description || '',
        thingType:   n.thingType || 'atomic',
        isDark,
      },
      position: { x: 0, y: 0 },
    }))
    const nodeIdSet = new Set(rfNodes.map((n) => n.id))
    const rfEdges   = buildEdges(graphData.edges || [], nodeIdSet, isDark)
    const laidOut   = computeLayout(rfNodes, rfEdges, direction)

    setNodes(laidOut)
    setEdges(rfEdges)
  }, [graphData, isDark, direction, setNodes, setEdges])

  const onNodeClick = useCallback((_e, node) => onNodeSelect(node.data), [onNodeSelect])
  const onPaneClick = useCallback(() => onNodeSelect(null), [onNodeSelect])

  return (
    <>
      {/* xyflow Controls + MiniMap default renklerini dark mode için override et */}
      <style>{`
        .react-flow__controls-button {
          background: ${C.headerBg} !important;
          border-bottom: 1px solid ${C.border} !important;
          color: ${C.textPrimary} !important;
          fill: ${C.textPrimary} !important;
          width: 30px !important;
          height: 30px !important;
          transition: background 0.15s ease;
        }
        .react-flow__controls-button:hover {
          background: ${isDark ? '#334155' : '#f1f5f9'} !important;
        }
        .react-flow__controls-button svg {
          fill: ${C.textPrimary} !important;
          max-width: 14px;
          max-height: 14px;
        }
        .react-flow__controls-button:disabled {
          opacity: 0.4;
        }
        .react-flow__minimap {
          background: ${C.headerBg} !important;
        }
        .react-flow__minimap-mask {
          fill: ${isDark ? 'rgba(15,23,42,0.55)' : 'rgba(241,245,249,0.55)'} !important;
        }
        .react-flow__attribution {
          background: transparent !important;
        }
        /* Node hover accent */
        .twin-node {
          will-change: transform, box-shadow;
        }
        .react-flow__node:hover .twin-node {
          transform: translateY(-2px) scale(1.025);
        }
        /* Edge label pill */
        .react-flow__edge-textbg {
          rx: 6px;
          ry: 6px;
        }
        .react-flow__edge-text {
          font-family: inherit;
        }
        /* Edge path soft shadow */
        .react-flow__edge-path {
          filter: ${isDark ? 'drop-shadow(0 0 2px rgba(0,0,0,0.4))' : 'drop-shadow(0 0 2px rgba(15,23,42,0.08))'};
        }
        /* Selected edge boost */
        .react-flow__edge.selected .react-flow__edge-path,
        .react-flow__edge:focus .react-flow__edge-path {
          stroke-width: 3.5 !important;
        }
      `}</style>
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={NODE_TYPES}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      colorMode={isDark ? 'dark' : 'light'}
      fitView
      fitViewOptions={{ padding: 0.25, duration: 400 }}
      minZoom={0.1}
      maxZoom={3}
      proOptions={{ hideAttribution: true }}
      deleteKeyCode={null}
      nodesDraggable={isInteractive}
      nodesConnectable={false}
      elementsSelectable={isInteractive}
      panOnDrag={isInteractive}
      zoomOnScroll
      zoomOnPinch
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={22}
        size={1.2}
        color={C.dotColor}
      />
      <Controls
        onInteractiveChange={(v) => setIsInteractive(v)}
        style={{
          background: C.headerBg,
          border: `1px solid ${C.border}`,
          borderRadius: 10,
          overflow: 'hidden',
          boxShadow: isDark ? '0 4px 16px rgba(0,0,0,0.45)' : '0 4px 14px rgba(15,23,42,0.08)',
        }}
      />
      <MiniMap
        nodeColor={(n) => (TYPE_META[n.data?.thingType] || UNKNOWN_META).hex}
        nodeStrokeColor={isDark ? '#0f172a' : '#ffffff'}
        nodeStrokeWidth={2}
        bgColor={C.headerBg}
        maskColor={C.miniMapMask}
        style={{
          background: C.headerBg,
          border: `1px solid ${C.border}`,
          borderRadius: 8,
        }}
      />
      <Panel position="bottom-center">
        <div style={{
          background: C.legendBg,
          border: `1px solid ${C.border}`,
          borderRadius: 10,
          padding: '7px 14px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px 16px',
          alignItems: 'center',
          fontSize: 11,
          boxShadow: '0 2px 10px rgba(0,0,0,0.10)',
        }}>
          {Object.entries(TYPE_META).map(([key, m]) => (
            <span key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 9, height: 9, borderRadius: '50%', background: m.hex, display: 'inline-block', flexShrink: 0 }} />
              <m.Icon size={10} color={C.textMuted} />
              <span style={{ color: C.textPrimary }}>{m.label}</span>
            </span>
          ))}
          <span style={{ width: 1, height: 14, background: C.border, display: 'inline-block' }} />
          {Object.entries(REL_COLORS).map(([k, c]) => (
            <span key={k} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 18, height: 2.5, background: c, borderRadius: 2, display: 'inline-block', flexShrink: 0 }} />
              <span style={{ color: C.textPrimary }}>{k}</span>
            </span>
          ))}
        </div>
      </Panel>
    </ReactFlow>
    </>
  )
}

// ─── Main page component ───────────────────────────────────────────────────────
export default function TwinGraphView() {
  const navigate        = useNavigate()
  const { toast }       = useToast()
  const currentTenant   = useTenantStore((s) => s.currentTenant)
  const { isCollapsed } = useSidebarStore()

  const isDark = useIsDark()

  const sidebarW = isCollapsed ? 64 : 256
  const navbarH  = 64

  const [isLoading,    setIsLoading]    = useState(true)
  const [graphData,    setGraphData]    = useState(null)
  const [stats,        setStats]        = useState({ nodes: 0, edges: 0 })
  const [selectedNode, setSelectedNode] = useState(null)
  const [direction,    setDirection]    = useState(() => {
    return localStorage.getItem('twin-graph-direction') || 'LR'
  })

  const changeDirection = useCallback((d) => {
    setDirection(d)
    try { localStorage.setItem('twin-graph-direction', d) } catch { /* ignore */ }
  }, [])

  const loadGraph = useCallback(async () => {
    setIsLoading(true)
    setSelectedNode(null)
    try {
      const data = await TwinService.getTenantGraph()
      const fwdEdges = (data.edges || []).filter(
        (e) => !INVERSE_TYPES.has(e.relType) && e.sourceName && e.targetName
      )
      setStats({ nodes: (data.nodes || []).length, edges: fwdEdges.length })
      setGraphData(data)
    } catch (err) {
      toast({ variant: 'destructive', title: 'Graph yüklenemedi', description: err?.message || String(err) })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  useEffect(() => { loadGraph() }, [currentTenant, loadGraph])

  const C = useMemo(() => (isDark ? {
    pageBg: 'radial-gradient(ellipse at 20% 0%, #1e293b 0%, #0f172a 55%), #0f172a',
    headerBg: 'rgba(30,41,59,0.85)', border: '#334155',
    textPrimary: '#f1f5f9', textMuted: '#94a3b8', chipBg: 'rgba(51,65,85,0.8)', chipText: '#cbd5e1',
    legendBg: 'rgba(30,41,59,0.92)', dotColor: '#1e293b', miniMapMask: 'rgba(15,23,42,0.65)',
    accent: '#60a5fa',
  } : {
    pageBg: 'radial-gradient(ellipse at 20% 0%, #e0e7ff 0%, #f1f5f9 60%), #f1f5f9',
    headerBg: 'rgba(255,255,255,0.92)', border: '#e2e8f0',
    textPrimary: '#0f172a', textMuted: '#64748b', chipBg: 'rgba(241,245,249,0.85)', chipText: '#475569',
    legendBg: 'rgba(255,255,255,0.95)', dotColor: '#cbd5e1', miniMapMask: 'rgba(241,245,249,0.65)',
    accent: '#3b82f6',
  }), [isDark])

  return (
    <div style={{
      position: 'fixed',
      top: navbarH,
      left: sidebarW,
      right: 0,
      bottom: 0,
      display: 'flex',
      flexDirection: 'column',
      background: C.pageBg,
      transition: 'left 0.3s',
      zIndex: 10,
    }}>
      {/* Header */}
      <div style={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 18px',
        borderBottom: `1px solid ${C.border}`,
        background: C.headerBg,
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        flexShrink: 0,
        zIndex: 20,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 30,
            height: 30,
            borderRadius: 8,
            background: `linear-gradient(135deg, ${C.accent}33, ${C.accent}11)`,
            border: `1px solid ${C.accent}44`,
          }}>
            <Network size={15} color={C.accent} />
          </span>
          <span style={{ fontWeight: 700, fontSize: 16, color: C.textPrimary, letterSpacing: 0.2 }}>Tenant Graph</span>
          {currentTenant && (
            <span style={{
              background: C.chipBg,
              color: C.chipText,
              borderRadius: 7,
              padding: '3px 10px',
              fontSize: 12,
              fontWeight: 600,
              border: `1px solid ${C.border}`,
            }}>
              {currentTenant.tenant_id}
            </span>
          )}
          <span style={{ width: 1, height: 20, background: C.border }} />
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, color: C.textMuted, fontWeight: 500 }}>
            <Layers size={12} />
            <strong style={{ color: C.textPrimary, fontWeight: 700 }}>{stats.nodes}</strong> thing
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, color: C.textMuted, fontWeight: 500 }}>
            <GitBranch size={12} />
            <strong style={{ color: C.textPrimary, fontWeight: 700 }}>{stats.edges}</strong> ilişki
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {/* Layout direction toggle */}
          <div style={{
            display: 'inline-flex',
            background: C.chipBg,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            padding: 2,
            gap: 2,
          }}>
            <button
              onClick={() => changeDirection('LR')}
              title="Yatay düzen (soldan sağa)"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                padding: '4px 9px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background:  direction === 'LR' ? C.accent : 'transparent',
                color:       direction === 'LR' ? '#ffffff' : C.textMuted,
                fontSize:    11, fontWeight: 600,
                transition:  'background 0.15s',
              }}
            >
              <MoveHorizontal size={12} />
              LR
            </button>
            <button
              onClick={() => changeDirection('TB')}
              title="Dikey düzen (üstten alta)"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                padding: '4px 9px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background:  direction === 'TB' ? C.accent : 'transparent',
                color:       direction === 'TB' ? '#ffffff' : C.textMuted,
                fontSize:    11, fontWeight: 600,
                transition:  'background 0.15s',
              }}
            >
              <MoveVertical size={12} />
              TB
            </button>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate('/things')}>
            <List className="h-4 w-4 mr-1" />Liste
          </Button>
          <Button variant="outline" size="sm" onClick={loadGraph} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />Yenile
          </Button>
        </div>
      </div>

      {/* Canvas area */}
      <div style={{
        position: 'absolute',
        top: 56,
        left: 0,
        bottom: 0,
        right: selectedNode ? 288 : 0,
      }}>
        {isLoading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <RefreshCw size={32} className="animate-spin" style={{ color: '#60a5fa', margin: '0 auto 12px' }} />
              <p style={{ color: C.textMuted, fontSize: 14 }}>Graph yükleniyor…</p>
            </div>
          </div>
        ) : !graphData || graphData.nodes?.length === 0 ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <Layers size={48} style={{ color: C.textMuted, margin: '0 auto 12px' }} />
              <p style={{ color: C.textMuted, marginBottom: 12 }}>Bu tenant'ta henüz thing yok.</p>
              <Button size="sm" onClick={() => navigate('/things/create')}>İlk Thing'i Oluştur</Button>
            </div>
          </div>
        ) : (
          <ReactFlowProvider>
            <FlowCanvas
              graphData={graphData}
              isDark={isDark}
              direction={direction}
              onNodeSelect={setSelectedNode}
              C={C}
            />
          </ReactFlowProvider>
        )}
      </div>

      {/* Detail panel */}
      {selectedNode && (() => {
        const meta   = TYPE_META[selectedNode.thingType] || UNKNOWN_META
        const { Icon } = meta
        const bg     = isDark ? meta.darkBg     : meta.lightBg
        const border = isDark ? meta.darkBorder : meta.lightBorder
        const text   = isDark ? meta.darkText   : meta.lightText
        const badge  = isDark ? meta.darkBadge  : meta.lightBadge
        return (
          <div style={{
            position: 'absolute', top: 52, right: 0, bottom: 0, width: 288,
            background: C.headerBg, borderLeft: `1px solid ${C.border}`,
            overflowY: 'auto', padding: 16,
            display: 'flex', flexDirection: 'column', gap: 12, zIndex: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 600, fontSize: 13, color: C.textPrimary, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Info size={14} color="#3b82f6" /> Detay
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: C.textMuted, display: 'flex', alignItems: 'center' }}
              >
                <X size={16} />
              </button>
            </div>
            <div style={{ background: bg, border: `2px solid ${border}`, borderRadius: 10, padding: '10px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <Icon size={14} color={border} />
                <span style={{ fontWeight: 700, fontSize: 13, color: text, wordBreak: 'break-all' }}>
                  {selectedNode.label}
                </span>
              </div>
              <span style={{ display: 'inline-block', background: badge, color: text, fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 99 }}>
                {meta.label}
              </span>
            </div>
            {selectedNode.description && (
              <div>
                <p style={{ fontSize: 11, color: C.textMuted, fontWeight: 600, marginBottom: 3 }}>Açıklama</p>
                <p style={{ fontSize: 13, color: C.textPrimary }}>{selectedNode.description}</p>
              </div>
            )}
            <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 12 }}>
              <Button
                size="sm"
                style={{ width: '100%' }}
                onClick={() => navigate(`/things/${selectedNode.label}`)}
              >
                Detay Sayfasına Git
              </Button>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
