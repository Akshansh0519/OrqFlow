import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, ChevronDown, ChevronRight, Database, Search, Code, FileText, Loader2, CheckCircle2 } from 'lucide-react';

interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
}

interface ToolCallCardProps {
  toolCall: ToolCall;
  isRunning?: boolean;
}

const TOOL_META: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  execute_readonly_sql:       { icon: Database, color: '#10b981', label: 'DB Query' },
  list_tables:                { icon: Database, color: '#10b981', label: 'List Tables' },
  inspect_database_schema:    { icon: Database, color: '#10b981', label: 'Schema Inspect' },
  get_table_sample_rows:      { icon: Database, color: '#10b981', label: 'Sample Rows' },
  web_search:                 { icon: Search,   color: '#00f0ff', label: 'Web Search' },
  fetch_url:                  { icon: Search,   color: '#00f0ff', label: 'Fetch URL' },
  read_file:                  { icon: FileText, color: '#8b5cf6', label: 'Read File' },
  write_file:                 { icon: FileText, color: '#8b5cf6', label: 'Write File' },
  list_files:                 { icon: FileText, color: '#8b5cf6', label: 'List Files' },
  lint_python:                { icon: Code,     color: '#f59e0b', label: 'Lint Python' },
};

function formatJson(val: unknown): string {
  try { return JSON.stringify(val, null, 2); }
  catch { return String(val); }
}

export const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall, isRunning = false }) => {
  const [expanded, setExpanded] = useState(false);
  const meta = TOOL_META[toolCall.name] || { icon: Terminal, color: '#f59e0b', label: toolCall.name };
  const Icon = meta.icon;
  const isDone = toolCall.result !== undefined;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 280, damping: 22 }}
      style={{
        background: 'rgba(0,0,0,0.55)',
        border: `1px solid ${isDone ? 'rgba(16,185,129,0.25)' : `${meta.color}33`}`,
        borderRadius: 10,
        marginBottom: '0.5rem',
        overflow: 'hidden',
        transition: 'border-color 0.2s ease',
      }}
    >
      {/* Header row */}
      <button
        onClick={() => setExpanded(v => !v)}
        style={{
          width: '100%',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '0.5rem 0.7rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        {/* Status indicator */}
        {isRunning && !isDone ? (
          <Loader2 size={13} style={{ color: meta.color, flexShrink: 0, animation: 'spin 1s linear infinite' }} />
        ) : isDone ? (
          <CheckCircle2 size={13} style={{ color: '#10b981', flexShrink: 0 }} />
        ) : (
          <Icon size={13} style={{ color: meta.color, flexShrink: 0 }} />
        )}

        {/* Tool label */}
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.72rem',
          color: meta.color,
          fontWeight: 600,
          letterSpacing: '0.03em',
        }}>
          MCP::{toolCall.name}
        </span>

        {/* Running shimmer pill */}
        {isRunning && !isDone && (
          <span className="shimmer" style={{
            fontSize: '0.62rem',
            color: '#475569',
            fontFamily: "'JetBrains Mono', monospace",
            padding: '0.1rem 0.45rem',
            borderRadius: 4,
            border: '1px solid rgba(255,255,255,0.06)',
            marginLeft: 'auto',
          }}>
            executing...
          </span>
        )}

        {/* Expand chevron */}
        <span style={{ marginLeft: isRunning && !isDone ? '0.3rem' : 'auto', color: '#475569' }}>
          {expanded
            ? <ChevronDown size={12} />
            : <ChevronRight size={12} />
          }
        </span>
      </button>

      {/* Expandable body */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              padding: '0 0.7rem 0.6rem',
              borderTop: '1px solid rgba(255,255,255,0.05)',
            }}>
              {/* Args section */}
              <div style={{ marginBottom: isDone ? '0.5rem' : 0 }}>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.65rem',
                  color: '#475569',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  marginBottom: '0.25rem',
                  marginTop: '0.45rem',
                }}>
                  Args
                </div>
                <pre style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.7rem',
                  color: '#64748b',
                  background: 'rgba(0,0,0,0.4)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: 6,
                  padding: '0.45rem 0.6rem',
                  margin: 0,
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  maxHeight: '7rem',
                }}>
                  {formatJson(toolCall.args)}
                </pre>
              </div>

              {/* Result section */}
              {isDone && (
                <div>
                  <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '0.65rem',
                    color: '#10b981',
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    marginBottom: '0.25rem',
                  }}>
                    Result
                  </div>
                  <pre style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '0.7rem',
                    color: '#4ade80',
                    background: 'rgba(16,185,129,0.05)',
                    border: '1px solid rgba(16,185,129,0.18)',
                    borderRadius: 6,
                    padding: '0.45rem 0.6rem',
                    margin: 0,
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                    maxHeight: '9rem',
                  }}>
                    {typeof toolCall.result === 'string'
                      ? toolCall.result
                      : formatJson(toolCall.result)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
