export const pricesStyles = {
  // ======================
  // BASE · CARDS
  // ======================

  card: {
    background: "rgba(11, 24, 48, 0.82)",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 22,
    padding: 18,
    marginBottom: 14,
    boxShadow: "0 10px 30px rgba(0,0,0,0.18)",
  },

  sectionTitle: {
    fontSize: 14,
    opacity: 0.72,
    marginBottom: 14,
    textAlign: "center",
  },

  pricesListCard: {
    background: "rgba(11, 24, 48, 0.82)",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 22,
    padding: 18,
    marginBottom: 14,
    boxShadow: "0 10px 30px rgba(0,0,0,0.18)",
  },

  pricesListTitle: {
    fontSize: 14,
    opacity: 0.72,
    marginBottom: 12,
  },

  // ======================
  // QUICK · SUMMARY
  // ======================

  quickRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "10px 0",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  },

  quickRowLast: {
    display: "flex",
    justifyContent: "space-between",
    paddingTop: 10,
  },

  quickLabel: {
    fontSize: 13,
    opacity: 0.7,
  },

  quickValue: {
    fontSize: 15,
    fontWeight: 700,
  },

  // ======================
  // QUICK CARDS
  // ======================

  quickCardsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
    marginBottom: 14,
  },

  quickCard: {
    background: "rgba(11, 24, 48, 0.82)",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 22,
    padding: 16,
    boxShadow: "0 10px 30px rgba(0,0,0,0.18)",
  },

  quickCardLabel: {
    fontSize: 12,
    opacity: 0.65,
    marginBottom: 8,
  },

  quickCardHour: {
    fontSize: 18,
    fontWeight: 700,
    lineHeight: 1.2,
    marginBottom: 6,
  },

  quickCardPrice: {
    fontSize: 15,
    fontWeight: 700,
  },

  // ======================
  // TABS
  // ======================

  tabsRow: {
    display: "flex",
    gap: 8,
    marginBottom: 14,
  },

  tabButton: {
    flex: 1,
    padding: "10px 12px",
    borderRadius: 14,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.04)",
    color: "#cbd5e1",
    fontSize: 13,
    fontWeight: 600,
    textAlign: "center",
    cursor: "pointer",
    transition: "all 0.2s ease",
  },

  tabButtonActive: {
    background: "rgba(59,130,246,0.16)",
    border: "1px solid rgba(59,130,246,0.35)",
    color: "#f8fafc",
    boxShadow: "0 8px 20px rgba(0,0,0,0.18)",
  },

  // ======================
  // PRICE LIST
  // ======================

  pricesList: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },

  priceBlock: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },

  priceRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 14px",
    background: "rgba(255,255,255,0.04)",
    borderRadius: 14,
    border: "1px solid rgba(255,255,255,0.03)",
    transition: "all 0.2s ease",
  },

  priceRowHover: {
    transform: "translateY(-1px)",
    background: "rgba(255,255,255,0.06)",
    boxShadow: "0 6px 18px rgba(0,0,0,0.25)",
  },

  priceRowClickable: {
    cursor: "pointer",
  },

  priceRowHour: {
    fontSize: 15,
    fontWeight: 600,
    color: "#f8fafc",
  },

  priceRowActions: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },

  priceRowRight: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    justifyContent: "center",
    gap: 3,
    width: 170,
  },

  priceMetaRow: {
    display: "flex",
    justifyContent: "flex-end",
    alignItems: "baseline",
    gap: 4,
    width: "100%",
  },

  priceMetaLabel: {
    fontSize: 11,
    fontWeight: 700,
    opacity: 0.72,
    color: "#cbd5e1",
    letterSpacing: "0.02em",
    whiteSpace: "nowrap",
  },

  priceOmie: {
    fontSize: 12,
    lineHeight: 1.15,
    fontWeight: 700,
    color: "#cbd5e1",
    textAlign: "right",
    whiteSpace: "nowrap",
  },

  priceFinal: {
    fontSize: 12,
    lineHeight: 1.15,
    fontWeight: 700,
    color: "#f8fafc",
    textAlign: "right",
    whiteSpace: "nowrap",
  },

  priceExpand: {
    width: 16,
    textAlign: "center",
    fontSize: 16,
    fontWeight: 700,
    color: "#94a3b8",
    opacity: 0.9,
    flexShrink: 0,
  },

  // ======================
  // PERIODS
  // ======================

  periodsPanel: {
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.03)",
    borderRadius: 14,
    padding: 10,
  },

  periodRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 4px",
    borderBottom: "1px solid rgba(255,255,255,0.05)",
  },

  periodLabel: {
    fontSize: 12,
    color: "#cbd5e1",
    opacity: 0.85,
  },

  periodValue: {
    fontSize: 12,
    fontWeight: 600,
    color: "#f8fafc",
  },

  // ======================
  // HELPERS · TONE
  // ======================

  getToneValueStyle: (price) => {
    if (price < 0.08) return { color: "#22c55e" };
    if (price < 0.13) return { color: "#f97316" };
    return { color: "#ef4444" };
  },

  getToneBorderStyle: (price) => {
    if (price < 0.08) {
      return {
        border: "1px solid rgba(34, 197, 94, 0.4)",
        boxShadow: "0 0 12px rgba(34, 197, 94, 0.15)",
      };
    }

    if (price < 0.13) {
      return {
        border: "1px solid rgba(249, 115, 22, 0.4)",
        boxShadow: "0 0 12px rgba(249, 115, 22, 0.15)",
      };
    }

    return {
      border: "1px solid rgba(239, 68, 68, 0.4)",
      boxShadow: "0 0 12px rgba(239, 68, 68, 0.15)",
    };
  },

  getToneRowAccentStyle: (price) => {
    if (price < 0.08) {
      return { borderLeft: "3px solid #22c55e" };
    }

    if (price < 0.13) {
      return { borderLeft: "3px solid #f97316" };
    }

    return { borderLeft: "3px solid #ef4444" };
  },
};