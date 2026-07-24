import { useState, useEffect } from "react";
import { Loader2, X } from "lucide-react";

type ServiceStatus = "CHECKING" | "WAKING_UP" | "ALL_ONLINE" | "DISMISSED";

const CONFIGURED_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function getApiBase() {
  if (CONFIGURED_API_BASE_URL) return CONFIGURED_API_BASE_URL;
  if (window.location.port === "5173") return `http://${window.location.hostname}:8000`;
  return "";
}

export function BackendStatusBanner() {
  const [overallStatus, setOverallStatus] = useState<ServiceStatus>("CHECKING");
  const [attemptCount, setAttemptCount] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Small delay before showing so it slides in smoothly
    const showTimer = setTimeout(() => setVisible(true), 300);
    return () => clearTimeout(showTimer);
  }, []);

  useEffect(() => {
    let isMounted = true;
    let timer: ReturnType<typeof setTimeout>;

    const checkHealth = async () => {
      if (!isMounted) return;
      const apiBase = getApiBase();

      try {
        const res = await fetch(`${apiBase}/api/health`, { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          if (!isMounted) return;
          setOverallStatus("ALL_ONLINE");
        } else {
          throw new Error("Backend not OK");
        }
      } catch {
        if (!isMounted) return;
        setOverallStatus("WAKING_UP");
        setAttemptCount((prev) => prev + 1);
        timer = setTimeout(checkHealth, 3000);
      }
    };

    checkHealth();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (overallStatus === "DISMISSED") return null;

  const isWaking = overallStatus === "CHECKING" || overallStatus === "WAKING_UP";
  const displayAttempt = overallStatus === "CHECKING" ? 1 : attemptCount;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "1.5rem",
        right: "1.5rem",
        zIndex: 9999,
        maxWidth: "360px",
        width: "calc(100vw - 3rem)",
        fontFamily: "'Inter', sans-serif",
        transform: visible ? "translateY(0)" : "translateY(120%)",
        opacity: visible ? 1 : 0,
        transition: "transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s ease",
      }}
    >
      {/* Waking Up / Checking card */}
      {isWaking && (
        <div
          style={{
            background: "rgba(12, 18, 28, 0.97)",
            backdropFilter: "blur(16px)",
            border: "1px solid rgba(245, 158, 11, 0.4)",
            borderRadius: "16px",
            padding: "1.1rem 1.2rem",
            boxShadow: "0 20px 60px -10px rgba(120, 80, 0, 0.35), 0 0 0 1px rgba(245, 158, 11, 0.08)",
            color: "#fff",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Top accent bar with animation via keyframes in style */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: "3px",
              background: "linear-gradient(90deg, #f59e0b, #fb923c, #fbbf24)",
              animation: "pulse 2s ease-in-out infinite",
            }}
          />

          {/* Header row */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              {/* Pulsing amber dot */}
              <span style={{ position: "relative", display: "inline-flex", width: "12px", height: "12px" }}>
                <span
                  style={{
                    position: "absolute",
                    inset: 0,
                    borderRadius: "50%",
                    background: "rgba(251, 191, 36, 0.5)",
                    animation: "ping 1s cubic-bezier(0, 0, 0.2, 1) infinite",
                  }}
                />
                <span
                  style={{
                    position: "relative",
                    display: "inline-flex",
                    width: "12px",
                    height: "12px",
                    borderRadius: "50%",
                    background: "#f59e0b",
                  }}
                />
              </span>
              <span style={{ fontWeight: 700, fontSize: "0.82rem", color: "#fcd34d", letterSpacing: "0.01em" }}>
                Render Free Tier Notice
              </span>
            </div>
            {/* Attempt badge */}
            <span
              style={{
                fontSize: "0.65rem",
                fontFamily: "'JetBrains Mono', monospace",
                background: "rgba(245,158,11,0.12)",
                color: "#fcd34d",
                padding: "0.2rem 0.55rem",
                borderRadius: "999px",
                border: "1px solid rgba(245,158,11,0.25)",
                whiteSpace: "nowrap",
              }}
            >
              Attempt #{displayAttempt}
            </span>
          </div>

          {/* Body */}
          <p style={{ fontSize: "0.75rem", color: "#cbd5e1", lineHeight: 1.6, margin: "0 0 0.75rem 0" }}>
            The API runs on{" "}
            <strong style={{ color: "#fff" }}>Render Free Tier</strong>. If inactive, the OrqFlow API takes{" "}
            <span style={{ color: "#fbbf24", fontWeight: 600 }}>~50 seconds to warm up</span>.
          </p>
          <p style={{ fontSize: "0.7rem", color: "#64748b", margin: "0 0 0.85rem 0", fontStyle: "italic" }}>
            Polling the backend every 3s until it responds…
          </p>

          {/* Footer */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderTop: "1px solid rgba(255,255,255,0.06)",
              paddingTop: "0.65rem",
            }}
          >
            <span style={{ fontSize: "0.68rem", color: "#64748b", display: "flex", alignItems: "center", gap: "0.3rem" }}>
              <Loader2 size={11} style={{ animation: "spin 1s linear infinite" }} />
              Checking every 3s
            </span>
            <button
              onClick={() => setOverallStatus("DISMISSED")}
              style={{
                fontSize: "0.68rem",
                color: "#64748b",
                background: "none",
                border: "none",
                cursor: "pointer",
                textDecoration: "underline",
                padding: 0,
              }}
            >
              Hide
            </button>
          </div>
        </div>
      )}

      {/* Online success card */}
      {overallStatus === "ALL_ONLINE" && (
        <div
          style={{
            background: "rgba(8, 20, 14, 0.97)",
            backdropFilter: "blur(16px)",
            border: "1px solid rgba(52, 211, 153, 0.5)",
            borderRadius: "16px",
            padding: "1.1rem 1.2rem",
            boxShadow: "0 20px 60px -10px rgba(0, 80, 40, 0.4), 0 0 0 1px rgba(52,211,153,0.08)",
            color: "#fff",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: "3px",
              background: "linear-gradient(90deg, #34d399, #2dd4bf, #10b981)",
            }}
          />

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.65rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <span style={{ position: "relative", display: "inline-flex", width: "12px", height: "12px" }}>
                <span
                  style={{
                    position: "absolute",
                    inset: 0,
                    borderRadius: "50%",
                    background: "rgba(52, 211, 153, 0.5)",
                    animation: "ping 1s cubic-bezier(0, 0, 0.2, 1) infinite",
                  }}
                />
                <span
                  style={{
                    position: "relative",
                    display: "inline-flex",
                    width: "12px",
                    height: "12px",
                    borderRadius: "50%",
                    background: "#10b981",
                  }}
                />
              </span>
              <span style={{ fontWeight: 700, fontSize: "0.82rem", color: "#6ee7b7" }}>
                Backend is Online!
              </span>
            </div>
            <button
              onClick={() => setOverallStatus("DISMISSED")}
              style={{
                background: "rgba(255,255,255,0.06)",
                border: "none",
                borderRadius: "8px",
                padding: "4px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                color: "#94a3b8",
              }}
            >
              <X size={14} />
            </button>
          </div>

          <p style={{ fontSize: "0.75rem", color: "#cbd5e1", lineHeight: 1.6, margin: "0 0 0.9rem 0" }}>
            The OrqFlow API returned{" "}
            <strong style={{ color: "#34d399" }}>200 OK</strong>. The multi-agent system is fully online.
          </p>

          <button
            onClick={() => setOverallStatus("DISMISSED")}
            style={{
              width: "100%",
              padding: "0.55rem",
              background: "linear-gradient(135deg, #059669 0%, #0d9488 100%)",
              border: "none",
              borderRadius: "10px",
              color: "#fff",
              fontSize: "0.75rem",
              fontWeight: 700,
              cursor: "pointer",
              letterSpacing: "0.03em",
              boxShadow: "0 4px 14px -4px rgba(16, 185, 129, 0.5)",
            }}
          >
            Got It, Continue to OrqFlow →
          </button>
        </div>
      )}
    </div>
  );
}
