import { useEffect, useMemo, useState } from "react";
import { styles } from "../styles";
import { pricesStyles } from "../styles/prices";
import { calculateFinalPricePerKwh } from "../lib/tariffs";
import {
  fetchHoursByDate,
  fetchPeriodsByDate,
  fetchPriceDaysHistory,
} from "../services/api";

// ╔════════════════════════════════════════════════════════════╗
// ║ HELPERS · FORMATTERS                                      ║
// ╚════════════════════════════════════════════════════════════╝

function toKwh(value) {
  if (value === undefined || value === null) return 0;

  const numericValue = Number(value);

  if (numericValue > 1) {
    return numericValue / 1000;
  }

  return numericValue;
}

function formatPrice(value) {
  if (value === undefined || value === null) return "0.00000";
  return Number(value).toFixed(5);
}

function formatHour(hour) {
  const start = String(hour - 1).padStart(2, "0");
  const end = String(hour).padStart(2, "0");
  return `${start}:00 - ${end}:00`;
}

function formatPeriod(period) {
  const totalMinutesStart = (period - 1) * 15;
  const totalMinutesEnd = totalMinutesStart + 15;

  const startHour = String(Math.floor(totalMinutesStart / 60)).padStart(2, "0");
  const startMinute = String(totalMinutesStart % 60).padStart(2, "0");

  const endHour = String(Math.floor(totalMinutesEnd / 60)).padStart(2, "0");
  const endMinute = String(totalMinutesEnd % 60).padStart(2, "0");

  return `${startHour}:${startMinute} - ${endHour}:${endMinute}`;
}

// ╔════════════════════════════════════════════════════════════╗
// ║ HELPERS · DATES                                           ║
// ╚════════════════════════════════════════════════════════════╝

function toIsoLocalDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date, days) {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + days);
  return nextDate;
}

// ╔════════════════════════════════════════════════════════════╗
// ║ HELPERS · PERIODS                                         ║
// ╚════════════════════════════════════════════════════════════╝

function groupPeriodsByHour(periodsData) {
  if (!periodsData?.periods) return {};

  const grouped = {};

  for (const p of periodsData.periods) {
    const hour = Math.ceil(p.period / 4);

    if (!grouped[hour]) {
      grouped[hour] = [];
    }

    grouped[hour].push(p);
  }

  return grouped;
}

// ╔════════════════════════════════════════════════════════════╗
// ║ HELPERS · HOURS                                           ║
// ╚════════════════════════════════════════════════════════════╝

function normalizeHours(hoursData) {
  if (!hoursData) return [];
  if (Array.isArray(hoursData)) return hoursData;
  if (Array.isArray(hoursData.hours)) return hoursData.hours;
  return [];
}

function buildHoursWithFinal(rawHours, date) {
  if (!date) return [];

  return rawHours.map((h) => ({
    hour: h.hour,
    omiePrice: h.price,
    finalPrice: calculateFinalPricePerKwh(h.price, date, h.hour),
  }));
}

function getBestHour(hours) {
  if (!hours.length) return null;
  return [...hours].sort((a, b) => a.finalPrice - b.finalPrice)[0];
}

function getWorstHour(hours) {
  if (!hours.length) return null;
  return [...hours].sort((a, b) => b.finalPrice - a.finalPrice)[0];
}

// ╔════════════════════════════════════════════════════════════╗
// ║ COMPONENT · PRICES                                        ║
// ╚════════════════════════════════════════════════════════════╝

function Prices() {
  // ──────────────────────────────
  // STATE
  // ──────────────────────────────

  const [hoursData, setHoursData] = useState(null);
  const [periodsData, setPeriodsData] = useState(null);
  const [tomorrowHoursData, setTomorrowHoursData] = useState(null);
  const [tomorrowPeriodsData, setTomorrowPeriodsData] = useState(null);

  const [historyDays, setHistoryDays] = useState([]);
  const [selectedHistoryDate, setSelectedHistoryDate] = useState("");
  const [historyHoursData, setHistoryHoursData] = useState(null);
  const [historyPeriodsData, setHistoryPeriodsData] = useState(null);

  const [error, setError] = useState("");
  const [expandedHour, setExpandedHour] = useState(null);
  const [activeTab, setActiveTab] = useState("today");

  // ──────────────────────────────
  // EFFECTS
  // ──────────────────────────────

  useEffect(() => {
    async function loadPrices() {
      try {
        setError("");

        const now = new Date();
        const todayDate = toIsoLocalDate(now);
        const tomorrowDate = toIsoLocalDate(addDays(now, 1));

        const [
          todayHours,
          todayPeriods,
          nextHours,
          nextPeriods,
          history,
        ] = await Promise.all([
          fetchHoursByDate(todayDate),
          fetchPeriodsByDate(todayDate),
          fetchHoursByDate(tomorrowDate),
          fetchPeriodsByDate(tomorrowDate),
          fetchPriceDaysHistory(30),
        ]);

        const historyList = history?.days || [];
        const defaultHistoryDate = historyList.length ? historyList[0].date : "";

        setHoursData(todayHours);
        setPeriodsData(todayPeriods);
        setTomorrowHoursData(nextHours);
        setTomorrowPeriodsData(nextPeriods);
        setHistoryDays(historyList);
        setSelectedHistoryDate(defaultHistoryDate);

        if (defaultHistoryDate) {
          const [historyHours, historyPeriods] = await Promise.all([
            fetchHoursByDate(defaultHistoryDate),
            fetchPeriodsByDate(defaultHistoryDate),
          ]);

          setHistoryHoursData(historyHours);
          setHistoryPeriodsData(historyPeriods);
        }
      } catch (err) {
        setError(err.message || "Error cargando precios");
      }
    }

    loadPrices();
  }, []);

  useEffect(() => {
    async function loadHistoryDate() {
      if (!selectedHistoryDate) return;

      try {
        const [historyHours, historyPeriods] = await Promise.all([
          fetchHoursByDate(selectedHistoryDate),
          fetchPeriodsByDate(selectedHistoryDate),
        ]);

        setHistoryHoursData(historyHours);
        setHistoryPeriodsData(historyPeriods);
        setExpandedHour(null);
      } catch (err) {
        setError(err.message || "Error cargando histórico");
      }
    }

    loadHistoryDate();
  }, [selectedHistoryDate]);

  // ──────────────────────────────
  // MEMOS · DATE
  // ──────────────────────────────

  const formattedDate = useMemo(() => {
    let sourceDate = null;

    if (activeTab === "today") {
      sourceDate = hoursData?.date;
    } else if (activeTab === "tomorrow") {
      sourceDate = tomorrowHoursData?.date;
    } else if (activeTab === "history") {
      sourceDate = null;
    }

    if (!sourceDate) return "";

    return new Date(sourceDate).toLocaleDateString("es-ES", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }, [activeTab, hoursData?.date, tomorrowHoursData?.date]);

  // ──────────────────────────────
  // MEMOS · HOURS
  // ──────────────────────────────

  const rawHours = useMemo(() => {
    return normalizeHours(hoursData);
  }, [hoursData]);

  const hoursWithFinal = useMemo(() => {
    return buildHoursWithFinal(rawHours, hoursData?.date);
  }, [rawHours, hoursData?.date]);

  const bestHour = useMemo(() => {
    return getBestHour(hoursWithFinal);
  }, [hoursWithFinal]);

  const worstHour = useMemo(() => {
    return getWorstHour(hoursWithFinal);
  }, [hoursWithFinal]);

  // ──────────────────────────────
  // MEMOS · TOMORROW
  // ──────────────────────────────

  const rawTomorrowHours = useMemo(() => {
    return normalizeHours(tomorrowHoursData);
  }, [tomorrowHoursData]);

  const tomorrowHoursWithFinal = useMemo(() => {
    return buildHoursWithFinal(rawTomorrowHours, tomorrowHoursData?.date);
  }, [rawTomorrowHours, tomorrowHoursData?.date]);

  const tomorrowBestHour = useMemo(() => {
    return getBestHour(tomorrowHoursWithFinal);
  }, [tomorrowHoursWithFinal]);

  const tomorrowWorstHour = useMemo(() => {
    return getWorstHour(tomorrowHoursWithFinal);
  }, [tomorrowHoursWithFinal]);

  const tomorrowPeriodsByHour = useMemo(() => {
    if (!tomorrowPeriodsData) return {};

    try {
      return groupPeriodsByHour(tomorrowPeriodsData);
    } catch {
      return {};
    }
  }, [tomorrowPeriodsData]);

  // ──────────────────────────────
  // MEMOS · PERIODS
  // ──────────────────────────────

  const periodsByHour = useMemo(() => {
    if (!periodsData) return {};

    try {
      return groupPeriodsByHour(periodsData);
    } catch {
      return {};
    }
  }, [periodsData]);

  // ──────────────────────────────
  // MEMOS · HISTORY
  // ──────────────────────────────

  const historyRows = useMemo(() => {
    return historyDays.map((day) => ({
      ...day,
      tone:
        day.avg_price < 0.08
          ? "cheap"
          : day.avg_price < 0.13
          ? "medium"
          : "expensive",
    }));
  }, [historyDays]);

  const rawHistoryHours = useMemo(() => {
    return normalizeHours(historyHoursData);
  }, [historyHoursData]);

  const historyHoursWithFinal = useMemo(() => {
    return buildHoursWithFinal(rawHistoryHours, historyHoursData?.date);
  }, [rawHistoryHours, historyHoursData?.date]);

  const historyPeriodsByHour = useMemo(() => {
    if (!historyPeriodsData) return {};

    try {
      return groupPeriodsByHour(historyPeriodsData);
    } catch {
      return {};
    }
  }, [historyPeriodsData]);

  const selectedHistoryDay = useMemo(() => {
    return historyDays.find((day) => day.date === selectedHistoryDate) || null;
  }, [historyDays, selectedHistoryDate]);

  // ──────────────────────────────
  // RENDER · ERROR
  // ──────────────────────────────

  if (error) {
    return (
      <div style={styles.page}>
        <div style={styles.phone}>
          <div style={styles.errorCard}>
            <div style={styles.errorTitle}>Error</div>
            <div style={styles.errorText}>{error}</div>
          </div>
        </div>
      </div>
    );
  }

  // ──────────────────────────────
  // RENDER · LOADING
  // ──────────────────────────────

  if (!hoursData) {
    return (
      <div style={styles.page}>
        <div style={styles.phone}>
          <div style={styles.loadingCard}>Cargando precios...</div>
        </div>
      </div>
    );
  }

  // ╔════════════════════════════════════════════════════════════╗
  // ║ RENDER · MAIN                                             ║
  // ╚════════════════════════════════════════════════════════════╝

  return (
    <div style={styles.page}>
      <div style={styles.phone}>
        {/* ────────────────────────────── */}
        {/* HEADER                        */}
        {/* ────────────────────────────── */}
        <header style={styles.appHeader}>
          <div style={styles.appName}>Precios</div>
          <div style={styles.appDate}>{formattedDate}</div>
        </header>

        {/* ────────────────────────────── */}
        {/* TABS                          */}
        {/* ────────────────────────────── */}
        <div style={pricesStyles.tabsRow}>
          <div
            style={{
              ...pricesStyles.tabButton,
              ...(activeTab === "today" ? pricesStyles.tabButtonActive : {}),
            }}
            onClick={() => setActiveTab("today")}
          >
            Hoy
          </div>

          <div
            style={{
              ...pricesStyles.tabButton,
              ...(activeTab === "tomorrow" ? pricesStyles.tabButtonActive : {}),
            }}
            onClick={() => setActiveTab("tomorrow")}
          >
            Mañana
          </div>

          <div
            style={{
              ...pricesStyles.tabButton,
              ...(activeTab === "history" ? pricesStyles.tabButtonActive : {}),
            }}
            onClick={() => setActiveTab("history")}
          >
            Histórico
          </div>
        </div>

        {/* ────────────────────────────── */}
        {/* TODAY                         */}
        {/* ────────────────────────────── */}
        {activeTab === "today" && (
          <>
            {/* ────────────────────────────── */}
            {/* QUICK CARDS                   */}
            {/* ────────────────────────────── */}
            <div style={pricesStyles.quickCardsGrid}>
              <div
                style={{
                  ...pricesStyles.quickCard,
                  ...(bestHour
                    ? pricesStyles.getToneBorderStyle(bestHour.finalPrice)
                    : {}),
                }}
              >
                <div style={pricesStyles.quickCardLabel}>Mejor hora</div>
                <div style={pricesStyles.quickCardHour}>
                  {bestHour ? formatHour(bestHour.hour) : "--"}
                </div>
                <div
                  style={{
                    ...pricesStyles.quickCardPrice,
                    ...(bestHour
                      ? pricesStyles.getToneValueStyle(bestHour.finalPrice)
                      : {}),
                  }}
                >
                  {bestHour ? formatPrice(bestHour.finalPrice) : "--"}
                </div>
              </div>

              <div
                style={{
                  ...pricesStyles.quickCard,
                  ...(worstHour
                    ? pricesStyles.getToneBorderStyle(worstHour.finalPrice)
                    : {}),
                }}
              >
                <div style={pricesStyles.quickCardLabel}>Peor hora</div>
                <div style={pricesStyles.quickCardHour}>
                  {worstHour ? formatHour(worstHour.hour) : "--"}
                </div>
                <div
                  style={{
                    ...pricesStyles.quickCardPrice,
                    ...(worstHour
                      ? pricesStyles.getToneValueStyle(worstHour.finalPrice)
                      : {}),
                  }}
                >
                  {worstHour ? formatPrice(worstHour.finalPrice) : "--"}
                </div>
              </div>
            </div>

            {/* ────────────────────────────── */}
            {/* PRICE LIST                    */}
            {/* ────────────────────────────── */}
            <section style={pricesStyles.pricesListCard}>
              <div style={pricesStyles.pricesListTitle}>Precio por hora</div>

              {hoursWithFinal.length === 0 ? (
                <div style={pricesStyles.emptyMessage}>
                  Aún no hay datos disponibles para este día
                </div>
              ) : (
                <div style={pricesStyles.pricesList}>
                  {hoursWithFinal.map((h) => {
                    const toneStyle = pricesStyles.getToneValueStyle(
                      h.finalPrice
                    );
                    const quarters = periodsByHour[h.hour] || [];
                    const isExpanded = expandedHour === h.hour;
                    const canExpand = quarters.length > 0;

                    return (
                      <div key={h.hour} style={pricesStyles.priceBlock}>
                        {/* ────────────────────────────── */}
                        {/* PRICE ROW                     */}
                        {/* ────────────────────────────── */}
                        <div
                          style={{
                            ...pricesStyles.priceRow,
                            ...(canExpand
                              ? pricesStyles.priceRowClickable
                              : {}),
                            ...pricesStyles.getToneRowAccentStyle(h.finalPrice),
                            ...(isExpanded ? pricesStyles.priceRowHover : {}),
                          }}
                          onClick={() => {
                            if (!canExpand) return;
                            setExpandedHour(isExpanded ? null : h.hour);
                          }}
                        >
                          <div style={pricesStyles.priceRowHour}>
                            {formatHour(h.hour)}
                          </div>

                          <div style={pricesStyles.priceRowActions}>
                            <div style={pricesStyles.priceRowRight}>
                              <div style={pricesStyles.priceMetaRow}>
                                <div style={pricesStyles.priceMetaLabel}>
                                  OMIE
                                </div>
                                <div style={pricesStyles.priceOmie}>
                                  {formatPrice(h.omiePrice)} €/kWh
                                </div>
                              </div>

                              <div style={pricesStyles.priceMetaRow}>
                                <div style={pricesStyles.priceMetaLabel}>
                                  Final
                                </div>
                                <div
                                  style={{
                                    ...pricesStyles.priceFinal,
                                    ...toneStyle,
                                  }}
                                >
                                  {formatPrice(h.finalPrice)} €/kWh
                                </div>
                              </div>
                            </div>

                            <div style={pricesStyles.priceExpand}>
                              {canExpand ? (isExpanded ? "−" : "+") : ""}
                            </div>
                          </div>
                        </div>

                        {/* ────────────────────────────── */}
                        {/* PERIODS DROPDOWN              */}
                        {/* ────────────────────────────── */}
                        {isExpanded && canExpand && (
                          <div style={pricesStyles.periodsPanel}>
                            {quarters.map((q) => (
                              <div
                                key={`${h.hour}-${q.period}`}
                                style={pricesStyles.periodRow}
                              >
                                <div style={pricesStyles.periodLabel}>
                                  {formatPeriod(q.period)}
                                </div>

                                <div style={pricesStyles.periodValue}>
                                  {formatPrice(toKwh(q.price))} €/kWh
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        )}

        {/* ────────────────────────────── */}
        {/* TOMORROW                      */}
        {/* ────────────────────────────── */}
        {activeTab === "tomorrow" && (
          <>
            {/* ────────────────────────────── */}
            {/* QUICK CARDS                   */}
            {/* ────────────────────────────── */}
            <div style={pricesStyles.quickCardsGrid}>
              <div
                style={{
                  ...pricesStyles.quickCard,
                  ...(tomorrowBestHour
                    ? pricesStyles.getToneBorderStyle(
                        tomorrowBestHour.finalPrice
                      )
                    : {}),
                }}
              >
                <div style={pricesStyles.quickCardLabel}>Mejor hora</div>
                <div style={pricesStyles.quickCardHour}>
                  {tomorrowBestHour ? formatHour(tomorrowBestHour.hour) : "--"}
                </div>
                <div
                  style={{
                    ...pricesStyles.quickCardPrice,
                    ...(tomorrowBestHour
                      ? pricesStyles.getToneValueStyle(
                          tomorrowBestHour.finalPrice
                        )
                      : {}),
                  }}
                >
                  {tomorrowBestHour
                    ? formatPrice(tomorrowBestHour.finalPrice)
                    : "--"}
                </div>
              </div>

              <div
                style={{
                  ...pricesStyles.quickCard,
                  ...(tomorrowWorstHour
                    ? pricesStyles.getToneBorderStyle(
                        tomorrowWorstHour.finalPrice
                      )
                    : {}),
                }}
              >
                <div style={pricesStyles.quickCardLabel}>Peor hora</div>
                <div style={pricesStyles.quickCardHour}>
                  {tomorrowWorstHour ? formatHour(tomorrowWorstHour.hour) : "--"}
                </div>
                <div
                  style={{
                    ...pricesStyles.quickCardPrice,
                    ...(tomorrowWorstHour
                      ? pricesStyles.getToneValueStyle(
                          tomorrowWorstHour.finalPrice
                        )
                      : {}),
                  }}
                >
                  {tomorrowWorstHour
                    ? formatPrice(tomorrowWorstHour.finalPrice)
                    : "--"}
                </div>
              </div>
            </div>

            {/* ────────────────────────────── */}
            {/* PRICE LIST                    */}
            {/* ────────────────────────────── */}
            <section style={pricesStyles.pricesListCard}>
              <div style={pricesStyles.pricesListTitle}>Precio por hora</div>

              {tomorrowHoursWithFinal.length === 0 ? (
                <div style={pricesStyles.emptyMessage}>
                  Aún no hay datos de mañana
                </div>
              ) : (
                <div style={pricesStyles.pricesList}>
                  {tomorrowHoursWithFinal.map((h) => {
                    const toneStyle = pricesStyles.getToneValueStyle(
                      h.finalPrice
                    );
                    const quarters = tomorrowPeriodsByHour[h.hour] || [];
                    const isExpanded = expandedHour === h.hour;
                    const canExpand = quarters.length > 0;

                    return (
                      <div key={h.hour} style={pricesStyles.priceBlock}>
                        {/* ────────────────────────────── */}
                        {/* PRICE ROW                     */}
                        {/* ────────────────────────────── */}
                        <div
                          style={{
                            ...pricesStyles.priceRow,
                            ...(canExpand
                              ? pricesStyles.priceRowClickable
                              : {}),
                            ...pricesStyles.getToneRowAccentStyle(h.finalPrice),
                            ...(isExpanded ? pricesStyles.priceRowHover : {}),
                          }}
                          onClick={() => {
                            if (!canExpand) return;
                            setExpandedHour(isExpanded ? null : h.hour);
                          }}
                        >
                          <div style={pricesStyles.priceRowHour}>
                            {formatHour(h.hour)}
                          </div>

                          <div style={pricesStyles.priceRowActions}>
                            <div style={pricesStyles.priceRowRight}>
                              <div style={pricesStyles.priceMetaRow}>
                                <div style={pricesStyles.priceMetaLabel}>
                                  OMIE
                                </div>
                                <div style={pricesStyles.priceOmie}>
                                  {formatPrice(h.omiePrice)} €/kWh
                                </div>
                              </div>

                              <div style={pricesStyles.priceMetaRow}>
                                <div style={pricesStyles.priceMetaLabel}>
                                  Final
                                </div>
                                <div
                                  style={{
                                    ...pricesStyles.priceFinal,
                                    ...toneStyle,
                                  }}
                                >
                                  {formatPrice(h.finalPrice)} €/kWh
                                </div>
                              </div>
                            </div>

                            <div style={pricesStyles.priceExpand}>
                              {canExpand ? (isExpanded ? "−" : "+") : ""}
                            </div>
                          </div>
                        </div>

                        {/* ────────────────────────────── */}
                        {/* PERIODS DROPDOWN              */}
                        {/* ────────────────────────────── */}
                        {isExpanded && canExpand && (
                          <div style={pricesStyles.periodsPanel}>
                            {quarters.map((q) => (
                              <div
                                key={`${h.hour}-${q.period}`}
                                style={pricesStyles.periodRow}
                              >
                                <div style={pricesStyles.periodLabel}>
                                  {formatPeriod(q.period)}
                                </div>

                                <div style={pricesStyles.periodValue}>
                                  {formatPrice(toKwh(q.price))} €/kWh
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        )}

        {/* ────────────────────────────── */}
        {/* HISTORY                       */}
        {/* ────────────────────────────── */}
        {activeTab === "history" && (
          <>
            <section style={pricesStyles.pricesListCard}>
              <div style={pricesStyles.pricesListTitle}>Histórico</div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <input
                  type="date"
                  value={selectedHistoryDate}
                  onChange={(e) => setSelectedHistoryDate(e.target.value)}
                  style={{
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 14,
                    padding: "12px 14px",
                    color: "#f8fafc",
                    fontSize: 14,
                    outline: "none",
                  }}
                />

                {selectedHistoryDay && (
                  <div style={pricesStyles.priceBlock}>
                    <div
                      style={{
                        ...pricesStyles.priceRow,
                        ...pricesStyles.getToneRowAccentStyle(
                          selectedHistoryDay.avg_price
                        ),
                      }}
                    >
                      <div style={pricesStyles.priceRowHour}>Resumen</div>

                      <div style={pricesStyles.priceRowRight}>
                        <div style={pricesStyles.priceMetaRow}>
                          <div style={pricesStyles.priceMetaLabel}>Mín</div>
                          <div style={pricesStyles.priceOmie}>
                            {formatPrice(selectedHistoryDay.min_price)} €/kWh
                          </div>
                        </div>

                        <div style={pricesStyles.priceMetaRow}>
                          <div style={pricesStyles.priceMetaLabel}>Media</div>
                          <div
                            style={{
                              ...pricesStyles.priceFinal,
                              ...pricesStyles.getToneValueStyle(
                                selectedHistoryDay.avg_price
                              ),
                            }}
                          >
                            {formatPrice(selectedHistoryDay.avg_price)} €/kWh
                          </div>
                        </div>

                        <div style={pricesStyles.priceMetaRow}>
                          <div style={pricesStyles.priceMetaLabel}>Máx</div>
                          <div style={pricesStyles.priceOmie}>
                            {formatPrice(selectedHistoryDay.max_price)} €/kWh
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>

            <section style={pricesStyles.pricesListCard}>
              <div style={pricesStyles.pricesListTitle}>Precio por hora</div>

              {historyHoursWithFinal.length === 0 ? (
                <div style={pricesStyles.emptyMessage}>
                  No hay datos disponibles para esta fecha
                </div>
              ) : (
                <div style={pricesStyles.pricesList}>
                  {historyHoursWithFinal.map((h) => {
                    const toneStyle = pricesStyles.getToneValueStyle(
                      h.finalPrice
                    );
                    const quarters = historyPeriodsByHour[h.hour] || [];
                    const isExpanded = expandedHour === h.hour;
                    const canExpand = quarters.length > 0;

                    return (
                      <div key={h.hour} style={pricesStyles.priceBlock}>
                        <div
                          style={{
                            ...pricesStyles.priceRow,
                            ...(canExpand
                              ? pricesStyles.priceRowClickable
                              : {}),
                            ...pricesStyles.getToneRowAccentStyle(h.finalPrice),
                            ...(isExpanded ? pricesStyles.priceRowHover : {}),
                          }}
                          onClick={() => {
                            if (!canExpand) return;
                            setExpandedHour(isExpanded ? null : h.hour);
                          }}
                        >
                          <div style={pricesStyles.priceRowHour}>
                            {formatHour(h.hour)}
                          </div>

                          <div style={pricesStyles.priceRowActions}>
                            <div style={pricesStyles.priceRowRight}>
                              <div style={pricesStyles.priceMetaRow}>
                                <div style={pricesStyles.priceMetaLabel}>
                                  OMIE
                                </div>
                                <div style={pricesStyles.priceOmie}>
                                  {formatPrice(h.omiePrice)} €/kWh
                                </div>
                              </div>

                              <div style={pricesStyles.priceMetaRow}>
                                <div style={pricesStyles.priceMetaLabel}>
                                  Final
                                </div>
                                <div
                                  style={{
                                    ...pricesStyles.priceFinal,
                                    ...toneStyle,
                                  }}
                                >
                                  {formatPrice(h.finalPrice)} €/kWh
                                </div>
                              </div>
                            </div>

                            <div style={pricesStyles.priceExpand}>
                              {canExpand ? (isExpanded ? "−" : "+") : ""}
                            </div>
                          </div>
                        </div>

                        {isExpanded && canExpand && (
                          <div style={pricesStyles.periodsPanel}>
                            {quarters.map((q) => (
                              <div
                                key={`${h.hour}-${q.period}`}
                                style={pricesStyles.periodRow}
                              >
                                <div style={pricesStyles.periodLabel}>
                                  {formatPeriod(q.period)}
                                </div>

                                <div style={pricesStyles.periodValue}>
                                  {formatPrice(toKwh(q.price))} €/kWh
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

export default Prices;