const COLORS = {
  cheap: "#22c55e",
  medium: "#f59e0b",
  expensive: "#ef4444",
  neutral: "#f8fafc",
};

export const homeStyles = {
  heroCard: {
    borderRadius: "20px",
    padding: "28px 22px",
    boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
    border: "1px solid rgba(255,255,255,0.04)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    textAlign: "center",
    width: "100%",
    boxSizing: "border-box",
  },

  getHeroCardStyle: (tone) => ({
    background:
      tone === "cheap"
        ? "linear-gradient(135deg, rgba(34,197,94,0.15) 0%, #0f172a 100%)"
        : tone === "medium"
          ? "linear-gradient(135deg, rgba(245,158,11,0.15) 0%, #0f172a 100%)"
          : tone === "expensive"
            ? "linear-gradient(135deg, rgba(239,68,68,0.15) 0%, #0f172a 100%)"
            : "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
  }),

  heroTop: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
  },

  heroLabel: {
    fontSize: "11px",
    color: "#94a3b8",
    marginBottom: "10px",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    textAlign: "center",
  },

  heroValue: {
    fontSize: "48px",
    fontWeight: "800",
    lineHeight: 1.1,
    letterSpacing: "-0.02em",
    textAlign: "center",
  },

  getHeroValueStyle: (tone) => ({
    color: COLORS[tone] || COLORS.neutral,
  }),

  heroUnit: {
    fontSize: "14px",
    color: "#94a3b8",
    marginTop: "8px",
    textAlign: "center",
  },

  infoCard: {
    background: "#0f172a",
    borderRadius: "16px",
    padding: "18px",
    border: "1px solid rgba(255,255,255,0.04)",
    width: "100%",
    boxSizing: "border-box",
  },

  infoTitle: {
    fontSize: "14px",
    fontWeight: "700",
    color: "#e2e8f0",
    marginBottom: "8px",
    textAlign: "center",
  },

  infoText: {
    fontSize: "13px",
    color: "#94a3b8",
    lineHeight: "1.5",
    textAlign: "center",
  },

  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    gap: "10px",
    width: "100%",
    boxSizing: "border-box",
  },

  metricCard: {
    background: "#0f172a",
    borderRadius: "16px",
    padding: "16px",
    textAlign: "center",
    border: "1px solid rgba(255,255,255,0.04)",
    width: "100%",
    boxSizing: "border-box",
    minWidth: 0,
  },

  metricLabel: {
    fontSize: "12px",
    color: "#64748b",
    marginBottom: "6px",
  },

  metricValue: {
    fontSize: "26px",
    fontWeight: "800",
    color: "#f1f5f9",
  },

  metricUnit: {
    fontSize: "12px",
    color: "#64748b",
  },
};