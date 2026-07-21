import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Search, Database, Code, MessageSquare, ChevronRight } from 'lucide-react';

interface TopologyBarProps {
  activeNode: string | null;
  nextRoute: string | null;
}

const NODES = [
  { id: 'supervisor', label: 'Supervisor', icon: Shield,       color: '#8b5cf6', glow: 'rgba(139,92,246,0.6)'  },
  { id: 'researcher', label: 'Researcher', icon: Search,       color: '#00f0ff', glow: 'rgba(0,240,255,0.5)'   },
  { id: 'analyst',    label: 'Analyst',    icon: Database,     color: '#10b981', glow: 'rgba(16,185,129,0.5)'  },
  { id: 'coder',      label: 'Coder',      icon: Code,         color: '#f59e0b', glow: 'rgba(245,158,11,0.5)'  },
  { id: 'responder',  label: 'Responder',  icon: MessageSquare,color: '#ec4899', glow: 'rgba(236,72,153,0.5)'  },
];

export const TopologyBar: React.FC<TopologyBarProps> = ({ activeNode, nextRoute }) => {
  const effectiveActive = activeNode || nextRoute;

  return (
    <div
      className="glass-card"
      style={{
        padding: '0.75rem 1.1rem',
        marginBottom: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
      }}
    >
      {/* Label row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.62rem',
          letterSpacing: '0.12em',
          color: '#475569',
          textTransform: 'uppercase',
          fontWeight: 600,
        }}>
          OrqFlow Topology
        </span>

        <AnimatePresence mode="wait">
          {nextRoute && (
            <motion.span
              key={nextRoute}
              initial={{ opacity: 0, x: 6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -6 }}
              transition={{ duration: 0.18 }}
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '0.65rem',
                color: '#8b5cf6',
                background: 'rgba(139,92,246,0.10)',
                border: '1px solid rgba(139,92,246,0.28)',
                padding: '0.18rem 0.6rem',
                borderRadius: 20,
                letterSpacing: '0.04em',
              }}
            >
              Routing → {nextRoute}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Node chain */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
        {NODES.map((node, idx) => {
          const Icon = node.icon;
          const isActive = effectiveActive === node.id;

          return (
            <React.Fragment key={node.id}>
              <motion.div
                animate={isActive ? {
                  y: -4,
                  scale: 1.06,
                } : {
                  y: 0,
                  scale: 1,
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 18 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.38rem',
                  padding: '0.38rem 0.75rem',
                  borderRadius: 9,
                  border: `1px solid ${isActive ? node.color : 'rgba(255,255,255,0.06)'}`,
                  background: isActive
                    ? `${node.color}12`
                    : 'rgba(255,255,255,0.02)',
                  boxShadow: isActive ? `0 0 20px -4px ${node.glow}` : 'none',
                  transition: 'border-color 0.22s ease, background 0.22s ease, box-shadow 0.22s ease',
                  cursor: 'default',
                  position: 'relative',
                  overflow: 'visible',
                }}
              >
                {/* Pulsing ring when active */}
                {isActive && (
                  <motion.div
                    initial={{ scale: 1, opacity: 0.6 }}
                    animate={{ scale: 1.9, opacity: 0 }}
                    transition={{ duration: 1.2, repeat: Infinity, ease: 'easeOut' }}
                    style={{
                      position: 'absolute',
                      inset: 0,
                      borderRadius: 9,
                      border: `1px solid ${node.color}`,
                      pointerEvents: 'none',
                    }}
                  />
                )}

                <Icon
                  size={13}
                  style={{
                    color: isActive ? node.color : '#334155',
                    transition: 'color 0.22s ease',
                    flexShrink: 0,
                  }}
                />
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.7rem',
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? node.color : '#334155',
                  transition: 'color 0.22s ease',
                  whiteSpace: 'nowrap',
                }}>
                  {node.label}
                </span>
              </motion.div>

              {/* Connector arrow */}
              {idx < NODES.length - 1 && (
                <ChevronRight
                  size={10}
                  style={{
                    color: isActive ? node.color : '#1e293b',
                    flexShrink: 0,
                    transition: 'color 0.22s ease',
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
