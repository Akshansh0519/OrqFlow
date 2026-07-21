import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

function CodeBlock({ language, children }: { language: string; children: string }) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  return (
    <div className="relative group my-2" style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.07)' }}>
      {/* Header bar */}
      <div style={{
        background: 'rgba(0,0,0,0.75)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        padding: '0.3rem 0.85rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.7rem',
          color: '#8b5cf6',
          fontWeight: 600,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: copied ? '#10b981' : '#475569',
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            fontSize: '0.7rem',
            fontFamily: "'JetBrains Mono', monospace",
            transition: 'color 0.15s ease',
            padding: '0.1rem 0.3rem',
          }}
          onMouseEnter={e => { if (!copied) (e.currentTarget as HTMLButtonElement).style.color = '#94a3b8'; }}
          onMouseLeave={e => { if (!copied) (e.currentTarget as HTMLButtonElement).style.color = '#475569'; }}
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          background: '#05050a',
          fontSize: '0.775rem',
          lineHeight: '1.65',
          padding: '0.85rem 1rem',
        }}
        codeTagProps={{
          style: { fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }
        }}
        showLineNumbers={children.split('\n').length > 4}
        lineNumberStyle={{ color: '#2d3748', fontSize: '0.68rem', minWidth: '2rem' }}
        wrapLongLines={false}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  return (
    <div className="agent-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Links
          a: ({ node: _n, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer" />
          ),
          // Tables — wrap in overflow div
          table: ({ node: _n, ...props }) => (
            <div style={{ overflowX: 'auto', borderRadius: 8, border: '1px solid rgba(139,92,246,0.18)', marginTop: '0.5rem', marginBottom: '0.5rem' }}>
              <table {...props} />
            </div>
          ),
          // Code blocks (multi-line) and inline code
          code: ({ node: _n, className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '');
            const isBlock = className?.startsWith('language-') || String(children).includes('\n');
            if (isBlock) {
              return (
                <CodeBlock language={match?.[1] || ''}>
                  {String(children).replace(/\n$/, '')}
                </CodeBlock>
              );
            }
            return <code className={className} {...props}>{children}</code>;
          },
          // HR
          hr: ({ node: _n, ...props }) => <hr {...props} />,
          // Strong
          strong: ({ node: _n, ...props }) => (
            <strong {...props} style={{ color: '#e2e8f0', fontWeight: 700 }} />
          ),
          // Em
          em: ({ node: _n, ...props }) => (
            <em {...props} style={{ color: '#94a3b8' }} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
