import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, Terminal, Activity, CheckCircle2, Zap } from 'lucide-react';

export interface TraceStep {
  step_index: number;
  node_name: string;
  event_type: string;
  tool_name?: string | null;
  latency_ms?: number | null;
  payload_preview?: string;
}

interface TraceInspectorProps {
  isOpen: boolean;
  onClose: () => void;
  runId: string | null;
  trace: TraceStep[];
  loading: boolean;
}

const NODE_COLORS: Record<string, string> = {
  supervisor:      '#8b5cf6',
  researcher:      '#00f0ff',
  analyst:         '#10b981',
  coder:           '#f59e0b',
  responder:       '#ec4899',
  fact_extraction: '#6366f1',
};

function getNodeColor(name: string): string {
  return NODE_COLORS[name.toLowerCase()] ?? '#475569';
}

function LatencyBadge({ ms }: { ms: number }) {
  const color = ms < 500 ? '#10b981' : ms < 2000 ? '#f59e0b' : '#ff2a2a';
  return (
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '0.65rem',
      color,
      display: 'flex',
      alignItems: 'center',
      gap: '0.2rem',
    }}>
      <Clock size={10} />
      {ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`}
    </span>
  );
}

export const TraceInspector: React.FC<TraceInspectorProps> = ({
  isOpen, onClose, runId, trace, loading,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="drawer"
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', stiffness: 260, damping: 28 }}
          style={{
            position: 'fixed',
            inset: '0 0 0 auto',
            width: 'min(420px, 100vw)',
            background: '#0a0a0a',
            borderLeft: '1px solid rgba(255,255,255,0.07)',
            boxShadow: '-8px 0 40px -8px rgba(139,92,246,0.15)',
            zIndex: 50,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Header */}
          <div style={{
            padding: '0.85rem 1rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            background: 'rgba(17,17,21,0.80)',
            backdropFilter: 'blur(16px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
              <Activity size={16} style={{ color: '#8b5cf6' }} />
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '0.78rem',
                fontWeight: 700,
                color: '#e2e8f0',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}>
                Execution Trace
              </span>
            </div>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 7,
                cursor: 'pointer',
                color: '#475569',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0.3rem',
                transition: 'color 0.15s ease, border-color 0.15s ease',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.color = '#e2e8f0';
                (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.20)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.color = '#475569';
                (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.08)';
              }}
            >
              <X size={15} />
            </button>
          </div>

          {/* Run meta */}
          <div style={{
            padding: '0.55rem 1rem',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            background: 'rgba(0,0,0,0.35)',
          }}>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.65rem',
              color: '#475569',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.18rem',
            }}>
              <span>
                <span style={{ color: '#2d3748' }}>run_id: </span>
                <span style={{ color: '#8b5cf6' }}>{runId ?? 'N/A'}</span>
              </span>
              <span>
                <span style={{ color: '#2d3748' }}>frames: </span>
                <span style={{ color: '#f8fafc', fontWeight: 600 }}>{trace.length}</span>
              </span>
            </div>
          </div>

          {/* Steps */}
          <div
            className="trace-scroll"
            style={{ flex: 1, overflowY: 'auto', padding: '0.85rem 1rem' }}
          >
            {loading ? (
              <div style={{
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                height: '12rem', gap: '0.75rem',
              }}>
                <div style={{
                  width: 28, height: 28,
                  border: '2px solid rgba(139,92,246,0.3)',
                  borderTop: '2px solid #8b5cf6',
                  borderRadius: '50%',
                  animation: 'spin 0.9s linear infinite',
                }} />
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.72rem',
                  color: '#475569',
                }}>
                  querying agent_steps...
                </span>
              </div>
            ) : trace.length === 0 ? (
              <div style={{
                textAlign: 'center', padding: '3rem 1rem',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '0.75rem', color: '#2d3748',
              }}>
                No trace events recorded yet.
              </div>
            ) : (
              <div style={{ position: 'relative' }}>
                {/* Timeline line */}
                <div style={{
                  position: 'absolute',
                  left: '0.8rem',
                  top: 0, bottom: 0,
                  width: 1,
                  background: 'linear-gradient(180deg, rgba(139,92,246,0.3) 0%, rgba(139,92,246,0.05) 100%)',
                }} />

                {trace.map((step, idx) => {
                  const nodeColor = getNodeColor(step.node_name);
                  const isTool = !!step.tool_name;

                  return (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.03, duration: 0.2 }}
                      style={{
                        display: 'flex',
                        gap: '0.85rem',
                        marginBottom: '0.7rem',
                        paddingLeft: '1.75rem',
                        position: 'relative',
                      }}
                    >
                      {/* Timeline dot */}
                      <div style={{
                        position: 'absolute',
                        left: '0.4rem',
                        top: '0.45rem',
                        width: 8, height: 8,
                        borderRadius: '50%',
                        background: nodeColor,
                        boxShadow: `0 0 8px 1px ${nodeColor}80`,
                        flexShrink: 0,
                      }} />

                      {/* Card */}
                      <div style={{
                        flex: 1,
                        background: 'rgba(255,255,255,0.025)',
                        border: `1px solid ${nodeColor}22`,
                        borderRadius: 9,
                        overflow: 'hidden',
                      }}>
                        {/* Step header */}
                        <div style={{
                          padding: '0.35rem 0.65rem',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '0.5rem',
                          borderBottom: isTool || step.payload_preview ? '1px solid rgba(255,255,255,0.04)' : 'none',
                        }}>
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: '0.66rem',
                            fontWeight: 700,
                            color: nodeColor,
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                          }}>
                            {step.step_index} · {step.node_name}
                          </span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <span style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: '0.6rem',
                              color: '#2d3748',
                              background: 'rgba(255,255,255,0.04)',
                              border: '1px solid rgba(255,255,255,0.05)',
                              padding: '0.06rem 0.35rem',
                              borderRadius: 4,
                            }}>
                              {step.event_type}
                            </span>
                            {typeof step.latency_ms === 'number' && (
                              <LatencyBadge ms={step.latency_ms} />
                            )}
                          </div>
                        </div>

                        {/* Tool row */}
                        {isTool && (
                          <div style={{
                            padding: '0.28rem 0.65rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.38rem',
                            background: 'rgba(245,158,11,0.05)',
                            borderBottom: step.payload_preview ? '1px solid rgba(255,255,255,0.04)' : 'none',
                          }}>
                            <Terminal size={11} style={{ color: '#f59e0b', flexShrink: 0 }} />
                            <span style={{
                              fontFamily: "'JetBrains Mono', monospace",
                              fontSize: '0.67rem',
                              color: '#f59e0b',
                            }}>
                              {step.tool_name}
                            </span>
                          </div>
                        )}

                        {/* Payload preview */}
                        {step.payload_preview && (
                          <pre style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: '0.65rem',
                            color: '#475569',
                            background: 'rgba(0,0,0,0.3)',
                            padding: '0.4rem 0.65rem',
                            margin: 0,
                            overflowX: 'auto',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all',
                            maxHeight: '6rem',
                          }}>
                            {step.payload_preview}
                          </pre>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div style={{
            padding: '0.55rem 1rem',
            borderTop: '1px solid rgba(255,255,255,0.05)',
            background: '#0a0a0a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.4rem',
          }}>
            <CheckCircle2 size={11} style={{ color: '#10b981' }} />
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.62rem',
              color: '#2d3748',
            }}>
              Evidence-based SQL audit log · PostgreSQL
            </span>
            <Zap size={10} style={{ color: '#8b5cf6', marginLeft: '0.3rem' }} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
