import { useEffect, useMemo, useState } from "react";
import { styles } from "../styles";
import { homeStyles } from "../styles/home";
import { calculateFinalPricePerKwh } from "../lib/tariffs";
import {
  fetchLatestPriceDay,
  fetchLatestHours,
  fetchSolarEdgeCurrent,
  fetchSolarEdgeQuartersToday,
  fetchSolarEdgeMonth,
} from "../services/api";


// ╔════════════════════════════════════════════════════════════╗
// ║ HELPERS                                                    ║
// ╚════════════════════════════════════════════════════════════╝

// ──────────────────────────────
// UNIT CONVERSION
// ──────────────────────────────

function toKwh(value) {
  if (value === undefined || value === null) return 0;
  const numericValue = Number(value);
  return numericValue > 1 ? numericValue / 1000 : numericValue;
}

function toKw(value) {
  if (value === undefined || value === null) return 0;
  return Number(value) / 1000;
}


// ──────────────────────────────
// FORMATTERS
// ──────────────────────────────

function formatPrice(value) {
  if (value === undefined || value === null) return "0.00000";
  return Number(value).toFixed(5);
}

function formatEnergy(value) {
  if (value === undefined || value === null) return "0.00";
  return Number(value).toFixed(2);
}


// ╔════════════════════════════════════════════════════════════╗
// ║ PRICE ENGINE                                               ║
// ╚════════════════════════════════════════════════════════════╝

// ──────────────────────────────
// FINAL PRICE PER HOUR
// ──────────────────────────────

function buildHoursWithFinal(hoursData) {
  if (!hoursData?.hours || !hoursData?.date) return [];

  return hoursData.hours.map((h) => {
    const omie = toKwh(h.price);

    return {
      hour: h.hour,
      omiePrice: omie,
      finalPrice: calculateFinalPricePerKwh(omie, hoursData.date, h.hour),
    };
  });
}


// ╔════════════════════════════════════════════════════════════╗
// ║ SOLAREDGE ENGINE                                           ║
// ╚════════════════════════════════════════════════════════════╝

// ──────────────────────────────
// REALTIME MESSAGE
// ──────────────────────────────

function getRealtimeMessage(excessKw, currentPrice) {
  if (excessKw >= 2) {
    return `Puedes añadir hasta ${formatEnergy(excessKw)} kW sin comprar red.`;
  }

  if (excessKw >= 0.5) {
    return `Tienes ${formatEnergy(excessKw)} kW disponibles. Bien para consumos moderados.`;
  }

  if (currentPrice <= 0.1) {
    return "Hay poco excedente, pero la red está barata.";
  }

  return "No hay excedente claro. Mejor evitar consumos fuertes.";
}


// ╔════════════════════════════════════════════════════════════╗
// ║ COMPONENT                                                  ║
// ╚════════════════════════════════════════════════════════════╝

function Home() {
  // ──────────────────────────────
  // STATE
  // ──────────────────────────────

  const [data, setData] = useState(null);
  const [hoursData, setHoursData] = useState(null);
  const [solarCurrent, setSolarCurrent] = useState(null);
  const [solarDay, setSolarDay] = useState(null);
  const [solarMonth, setSolarMonth] = useState(null);
  const [error, setError] = useState("");


  // ──────────────────────────────
  // DATA LOAD
  // ──────────────────────────────

  useEffect(() => {
    async function loadData() {
      try {
        setError("");

        const [day, hours, current, accumulatedDay, accumulatedMonth] =
          await Promise.all([
            fetchLatestPriceDay(),
            fetchLatestHours(),
            fetchSolarEdgeCurrent().catch(() => null),
            fetchSolarEdgeQuartersToday().catch(() => null),
            fetchSolarEdgeMonth().catch(() => null),
          ]);

        setData(day);
        setHoursData(hours);
        setSolarCurrent(current);
        setSolarDay(accumulatedDay);
        setSolarMonth(accumulatedMonth);
      } catch (err) {
        setError(err.message || "Error inesperado");
      }
    }

    loadData();
  }, []);


  // ──────────────────────────────
  // DERIVED DATE
  // ──────────────────────────────

  const formattedDate = useMemo(() => {
    if (!data?.date) return "";

    return new Date(data.date).toLocaleDateString("es-ES", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }, [data]);


  // ──────────────────────────────
  // DERIVED PRICE DATA
  // ──────────────────────────────

  const hoursWithFinalPrice = useMemo(() => {
    return buildHoursWithFinal(hoursData);
  }, [hoursData]);

  const currentHourData = useMemo(() => {
    if (!hoursWithFinalPrice?.length) return null;

    const now = new Date().getHours() + 1;
    return hoursWithFinalPrice.find((h) => h.hour === now);
  }, [hoursWithFinalPrice]);

  const currentPrice = currentHourData?.finalPrice ?? 0;


  // ──────────────────────────────
  // DERIVED SOLAREDGE DATA
  // ──────────────────────────────

  const productionKw = toKw(solarCurrent?.productionPowerW);
  const consumptionKw = toKw(solarCurrent?.consumptionPowerW);
  const excessKw = toKw(solarCurrent?.excessPowerW);
  const balanceKw = toKw(solarCurrent?.balancePowerW);

  const realtimeMessage = getRealtimeMessage(excessKw, currentPrice);


  // ──────────────────────────────
  // RENDER ERROR
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
  // RENDER LOADING
  // ──────────────────────────────

  if (!data || !hoursData) {
    return (
      <div style={styles.page}>
        <div style={styles.phone}>
          <div style={styles.loadingCard}>Cargando datos...</div>
        </div>
      </div>
    );
  }


  // ──────────────────────────────
  // RENDER PAGE
  // ──────────────────────────────

  return (
    <div style={styles.page}>
      <div style={styles.phone}>
        <header style={styles.appHeader}>
          <div style={styles.appName}>Smart Energy</div>
          <div style={styles.appDate}>{formattedDate}</div>
        </header>

        <section style={homeStyles.infoCard}>
          <div style={homeStyles.infoTitle}>Tiempo real</div>

          {solarCurrent ? (
            <>
              <div
                style={{
                  marginTop: 12,
                  fontSize: 32,
                  fontWeight: 900,
                  color: excessKw > 0.3 ? "#22c55e" : "#f59e0b",
                  textAlign: "center",
                }}
              >
                {formatEnergy(excessKw)} kW
              </div>

              <div style={homeStyles.infoText}>excedente disponible ahora</div>

              <div style={{ marginTop: 14, display: "grid", gap: 8 }}>
                <div>☀️ Producción: {formatEnergy(productionKw)} kW</div>
                <div>🏠 Consumo casa: {formatEnergy(consumptionKw)} kW</div>
                <div>
                  ⚖️ Balance: {balanceKw >= 0 ? "+" : ""}
                  {formatEnergy(balanceKw)} kW
                </div>
                {currentHourData && (
                  <div>
                    💶 Precio ahora: {formatPrice(currentHourData.finalPrice)} €/kWh
                  </div>
                )}
              </div>

              <div style={{ ...homeStyles.infoText, marginTop: 12 }}>
                {realtimeMessage}
              </div>
            </>
          ) : (
            <div style={homeStyles.infoText}>
              Datos SolarEdge pendientes de conectar.
            </div>
          )}
        </section>

        <section style={homeStyles.infoCard}>
          <div style={homeStyles.infoTitle}>Acumulado día</div>

          {solarDay ? (
            <>
              <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
                <div>☀️ Producción: {formatEnergy(solarDay.productionKwhUntilNow)} kWh</div>
                <div>🏠 Solar consumida: {formatEnergy(solarDay.selfConsumptionKwhUntilNow)} kWh</div>
                <div>📥 Red consumida: {formatEnergy(solarDay.purchasedKwhUntilNow)} kWh</div>
                <div>📤 Vertido a red: {formatEnergy(solarDay.feedInKwhUntilNow)} kWh</div>
              </div>

              <div style={{ ...homeStyles.infoText, marginTop: 12 }}>
                Datos acumulados hasta {solarDay.to?.slice(11, 16)}
              </div>
            </>
          ) : (
            <div style={homeStyles.infoText}>
              Acumulado diario pendiente de conectar.
            </div>
          )}
        </section>

        <section style={homeStyles.infoCard}>
          <div style={homeStyles.infoTitle}>Desde inicio contrato</div>

          {solarMonth ? (
            <>
              <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
                <div>☀️ Producción: {formatEnergy(solarMonth.productionKwhMonth)} kWh</div>
                <div>🏠 Solar consumida: {formatEnergy(solarMonth.selfConsumptionKwhMonth)} kWh</div>
                <div>📥 Red consumida: {formatEnergy(solarMonth.purchasedKwhMonth)} kWh</div>
                <div>📤 Vertido a red: {formatEnergy(solarMonth.feedInKwhMonth)} kWh</div>
              </div>

              <div style={{ ...homeStyles.infoText, marginTop: 12 }}>
                Desde 04/04/2026
              </div>
            </>
          ) : (
            <div style={homeStyles.infoText}>
              Acumulado desde inicio de contrato pendiente de conectar.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default Home;