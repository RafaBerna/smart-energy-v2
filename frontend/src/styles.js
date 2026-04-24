export const pricingConfig = {
  thresholds: {
    cheap: 0.09,
    medium: 0.15,
  },

  colors: {
    cheap: "#22c55e",
    medium: "#f59e0b",
    expensive: "#ef4444",
    neutral: "#94a3b8",
  },
};

export const styles = {
  page: {
    minHeight: "100vh",
    background: `
      radial-gradient(circle at 50% 0%, rgba(59,130,246,0.25), transparent 45%),
      radial-gradient(circle at 80% 80%, rgba(99,102,241,0.18), transparent 60%),
      linear-gradient(180deg, #020617 0%, #020617 100%)
    `,
    display: "flex",
    justifyContent: "center",
    alignItems: "flex-start",
    paddingTop: "max(20px, env(safe-area-inset-top))",
    paddingRight: "20px",
    paddingBottom: "max(20px, env(safe-area-inset-bottom))",
    paddingLeft: "20px",
    fontFamily:
      'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    boxSizing: "border-box",
  },

  phone: {
    width: "100%",
    maxWidth: "480px",
    display: "flex",
    flexDirection: "column",
    gap: "20px",
    paddingTop: "8px",
    boxSizing: "border-box",
  },

  appHeader: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "8px",
    marginBottom: "8px",
  },

  appName: {
    fontSize: "28px",
    fontWeight: "800",
    color: "#f1f5f9",
    letterSpacing: "-0.02em",
  },

  appDate: {
    fontSize: "14px",
    color: "#94a3b8",
    textTransform: "capitalize",
  },

  loadingCard: {
    background: "#0f172a",
    borderRadius: "16px",
    padding: "20px",
    textAlign: "center",
    color: "#e2e8f0",
  },

  errorCard: {
    background: "#7f1d1d",
    borderRadius: "16px",
    padding: "20px",
    color: "#fff",
  },

  errorTitle: {
    fontWeight: "700",
    marginBottom: "6px",
  },

  errorText: {
    fontSize: "13px",
  },

  appShell: {
    minHeight: "100vh",
  },

  screenContent: {
    paddingBottom: "calc(88px + env(safe-area-inset-bottom))",
  },

  bottomNav: {
    position: "fixed",
    left: "50%",
    bottom: "max(14px, env(safe-area-inset-bottom))",
    transform: "translateX(-50%)",
    width: "calc(100% - 24px)",
    maxWidth: "460px",
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "10px",
    padding: "10px",
    background: "rgba(6, 11, 27, 0.88)",
    backdropFilter: "blur(18px)",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: "22px",
    boxSizing: "border-box",
    boxShadow: "0 20px 40px rgba(0,0,0,0.35)",
  },

  getNavItemStyle: (isActive) => ({
    height: "48px",
    borderRadius: "14px",
    border: isActive
      ? "1px solid rgba(96,165,250,0.22)"
      : "1px solid rgba(255,255,255,0.04)",
    background: isActive
      ? "linear-gradient(180deg, rgba(37,99,235,0.30) 0%, rgba(29,78,216,0.18) 100%)"
      : "rgba(255,255,255,0.025)",
    color: isActive ? "#f8fafc" : "#94a3b8",
    fontSize: "13px",
    fontWeight: isActive ? "700" : "600",
    letterSpacing: "-0.01em",
    boxShadow: isActive ? "0 8px 18px rgba(37,99,235,0.18)" : "none",
  }),

  getBadgeStyle: (statusColor) => ({
    borderRadius: "999px",
    padding: "6px 10px",
    fontSize: "11px",
    fontWeight: "600",
    backgroundColor: `${statusColor}18`,
    color: statusColor,
    whiteSpace: "nowrap",
  }),

  getFinalPriceStyle: (tone) => {
    const palette = {
      cheap: pricingConfig.colors.cheap,
      medium: pricingConfig.colors.medium,
      expensive: pricingConfig.colors.expensive,
      neutral: "#f8fafc",
    };

    return {
      color: palette[tone] || palette.neutral,
      fontWeight: "800",
    };
  },
};