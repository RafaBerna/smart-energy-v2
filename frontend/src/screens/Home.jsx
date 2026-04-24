import { useEffect, useMemo, useState } from "react";
import { styles } from "../styles";
import { homeStyles } from "../styles/home";
import { calculateFinalPricePerKwh } from "../lib/tariffs";
import {
  fetchLatestPriceDay,
  fetchLatestHours,
  fetchWeatherByLocation,
} from "../services/api";

// ╔════════════════════════════════════════════════════════════╗
// ║ HELPERS · FORMATTERS                                                         ║
// ╚════════════════════════════════════════════════════════════╝

function toKwh(value) {
  if (value === undefined || value === null) return 0;
  const numericValue = Number(value);
  return numericValue > 1 ? numericValue / 1000 : numericValue;
}

function formatPrice(value) {
  if (value === undefined || value === null) return "0.00000";
  return Number(value).toFixed(5);
}

// ╔════════════════════════════════════════════════════════════╗
// ║ HELPERS · PRICE ENGINE                                                       ║
// ╚════════════════════════════════════════════════════════════╝

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
// ║ HELPERS · ANALYSIS                                                           ║
// ╚════════════════════════════════════════════════════════════╝

function buildDayAnalysis(hoursWithFinalPrice) {
  if (!hoursWithFinalPrice?.length) {
    return {
      avg: 0,
      min: 0,
      max: 0,
      bestHour: null,
      worstHour: null,
    };
  }

  const total = hoursWithFinalPrice.reduce((sum, h) => sum + h.finalPrice, 0);
  const avg = total / hoursWithFinalPrice.length;

  const bestHour = hoursWithFinalPrice.reduce((best, current) =>
    current.finalPrice < best.finalPrice ? current : best
  );

  const worstHour = hoursWithFinalPrice.reduce((worst, current) =>
    current.finalPrice > worst.finalPrice ? current : worst
  );

  return {
    avg,
    min: bestHour.finalPrice,
    max: worstHour.finalPrice,
    bestHour,
    worstHour,
  };
}

function buildPremiumConsumptionInsight(hoursWithFinalPrice) {
  if (!hoursWithFinalPrice?.length) {
    return {
      headline: "",
      subheadline: "",
      bestWindow: null,
      dayType: "neutral",
      actionText: "",
    };
  }

  const sortedHours = [...hoursWithFinalPrice].sort(
    (a, b) => a.finalPrice - b.finalPrice
  );

  const cheapestHours = sortedHours
    .slice(0, 4)
    .map((item) => item.hour)
    .sort((a, b) => a - b);

  const grouped = [];
  let currentGroup = [cheapestHours[0]];

  for (let i = 1; i < cheapestHours.length; i++) {
    if (cheapestHours[i] === cheapestHours[i - 1] + 1) {
      currentGroup.push(cheapestHours[i]);
    } else {
      grouped.push(currentGroup);
      currentGroup = [cheapestHours[i]];
    }
  }

  grouped.push(currentGroup);

  const bestGroup = grouped.sort((a, b) => {
    if (b.length !== a.length) return b.length - a.length;

    const avgA =
      a.reduce((sum, hour) => {
        const item = hoursWithFinalPrice.find((h) => h.hour === hour);
        return sum + item.finalPrice;
      }, 0) / a.length;

    const avgB =
      b.reduce((sum, hour) => {
        const item = hoursWithFinalPrice.find((h) => h.hour === hour);
        return sum + item.finalPrice;
      }, 0) / b.length;

    return avgA - avgB;
  })[0];

  const startHour = bestGroup[0];
  const endHour = bestGroup[bestGroup.length - 1];

  const bestWindow = {
    startHour,
    endHour,
    label: `${String(startHour - 1).padStart(2, "0")}:00 - ${String(
      endHour
    ).padStart(2, "0")}:00`,
  };

  const analysis = buildDayAnalysis(hoursWithFinalPrice);
  const range = analysis.max - analysis.min;

  if (range < 0.02) {
    return {
      headline: "Hoy el precio está bastante estable",
      subheadline: "No hace falta obsesionarse con la hora",
      bestWindow,
      dayType: "stable",
      actionText:
        "Si puedes, concentra consumo en las horas centrales más cómodas del día.",
    };
  }

  if (analysis.avg <= 0.1) {
    return {
      headline: "Hoy conviene consumir",
      subheadline: "Aprovecha la mejor franja del día",
      bestWindow,
      dayType: "cheap",
      actionText: `Pon lavadora, lavavajillas o consumos fuertes entre ${bestWindow.label}.`,
    };
  }

  if (analysis.avg <= 0.16) {
    return {
      headline: "Hoy conviene elegir bien la hora",
      subheadline: "Hay una franja claramente mejor",
      bestWindow,
      dayType: "normal",
      actionText: `Si puedes mover consumo, hazlo entre ${bestWindow.label}.`,
    };
  }

  return {
    headline: "Hoy mejor vigilar el consumo",
    subheadline: "Hay pocas horas realmente aprovechables",
    bestWindow,
    dayType: "expensive",
    actionText: `Evita consumos fuertes fuera de ${bestWindow.label}.`,
  };
}

// ╔════════════════════════════════════════════════════════════╗
// ║ COMPONENT · HOME                                                             ║
// ╚════════════════════════════════════════════════════════════╝

function Home() {
  // ──────────────────────────────
  // STATE
  // ──────────────────────────────

  const [data, setData] = useState(null);
  const [hoursData, setHoursData] = useState(null);
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState("");

  // ──────────────────────────────
  // EFFECTS
  // ──────────────────────────────

  useEffect(() => {
    async function loadData() {
      try {
        setError("");

        const location = "Sant Sadurní d'Anoia";

        const [day, hours] = await Promise.all([
          fetchLatestPriceDay(),
          fetchLatestHours(),
        ]);

        setData(day);
        setHoursData(hours);

        try {
          const weatherData = await fetchWeatherByLocation(location);
          setWeather(weatherData);
        } catch {
          setWeather(null);
        }
      } catch (err) {
        setError(err.message || "Error inesperado");
      }
    }

    loadData();
  }, []);

  // ──────────────────────────────
  // MEMOS · DATE
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
  // MEMOS · PRICES
  // ──────────────────────────────

  const hoursWithFinalPrice = useMemo(() => {
    return buildHoursWithFinal(hoursData);
  }, [hoursData]);

  const dayAnalysis = useMemo(() => {
    return buildDayAnalysis(hoursWithFinalPrice);
  }, [hoursWithFinalPrice]);

  const premiumInsight = useMemo(() => {
    return buildPremiumConsumptionInsight(hoursWithFinalPrice);
  }, [hoursWithFinalPrice]);

const currentHourData = useMemo(() => {
  if (!hoursWithFinalPrice?.length) return null;

  const now = new Date().getHours() + 1;

  return hoursWithFinalPrice.find((h) => h.hour === now);
}, [hoursWithFinalPrice]);

  // ──────────────────────────────
  // MEMOS · WEATHER
  // ──────────────────────────────

  const weatherCondition = weather?.energy?.condition;

  const heroTone = useMemo(() => {
    if (weatherCondition === "sun") return "cheap";
    if (weatherCondition === "cloud") return "medium";
    if (weatherCondition === "rain" || weatherCondition === "snow") {
      return "expensive";
    }

    if (premiumInsight.dayType === "cheap") return "cheap";
    if (premiumInsight.dayType === "normal") return "medium";
    if (premiumInsight.dayType === "expensive") return "expensive";

    return "neutral";
  }, [premiumInsight, weatherCondition]);

  const weatherIcon = useMemo(() => {
    if (weatherCondition === "sun") return "☀️";
    if (weatherCondition === "cloud") return "☁️";
    if (weatherCondition === "rain") return "🌧️";
    if (weatherCondition === "snow") return "❄️";
    return "🌤️";
  }, [weatherCondition]);

  const weatherTitle = useMemo(() => {
    if (weatherCondition === "sun") return "Buen día solar";
    if (weatherCondition === "cloud") return "Día mixto";
    if (weatherCondition === "rain") return "Hoy manda la red";
    if (weatherCondition === "snow") return "Producción solar muy baja";
    return "Estado energético del día";
  }, [weatherCondition]);

  const weatherText = useMemo(() => {
    if (weatherCondition === "sun") {
      return "Aprovecha las horas centrales para mover consumos a la franja solar.";
    }

    if (weatherCondition === "cloud") {
      return "Combina horas con algo de sol y tramos baratos de red.";
    }

    if (weatherCondition === "rain") {
      return "Hoy conviene priorizar las horas más baratas de la red.";
    }

    if (weatherCondition === "snow") {
      return "No cuentes con apoyo solar fuerte. Prioriza las horas baratas.";
    }

    return premiumInsight.actionText;
  }, [premiumInsight, weatherCondition]);

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

  if (!data || !hoursData) {
    return (
      <div style={styles.page}>
        <div style={styles.phone}>
          <div style={styles.loadingCard}>Cargando datos...</div>
        </div>
      </div>
    );
  }

  // ╔════════════════════════════════════════════════════════════╗
  // ║ RENDER · MAIN                                                                ║
  // ╚════════════════════════════════════════════════════════════╝

  return (
    <div style={styles.page}>
      <div style={styles.phone}>
        {/* ────────────────────────────── */}
        {/* HEADER                        */}
        {/* ────────────────────────────── */}
        <header style={styles.appHeader}>
          <div style={styles.appName}>Smart Energy</div>
          <div style={styles.appDate}>{formattedDate}</div>
        </header>

        {/* ────────────────────────────── */}
        {/* HERO                          */}
        {/* ────────────────────────────── */}
        <section
          style={{
            ...homeStyles.heroCard,
            ...homeStyles.getHeroCardStyle(heroTone),
          }}
        >
          <div style={homeStyles.heroTop}>
            <div>
              <div style={homeStyles.heroLabel}>
                {premiumInsight.subheadline}
              </div>

              <div
                style={{
                  ...homeStyles.heroValue,
                  ...homeStyles.getHeroValueStyle(heroTone),
                }}
              >
                {premiumInsight.bestWindow?.label || "--:-- - --:--"}
              </div>

              <div style={homeStyles.heroUnit}>
                {premiumInsight.headline}
              </div>
            </div>
          </div>
        </section>

       {/* ────────────────────────────── */}
       {/* CURRENT PRICE                 */}
       {/* ────────────────────────────── */}
       <section style={homeStyles.infoCard}>
        <div style={homeStyles.infoTitle}>Ahora mismo</div>

        {currentHourData ? (
         <div style={homeStyles.infoText}>
          {String(currentHourData.hour - 1).padStart(2, "0")}:00 -{" "}
          {String(currentHourData.hour).padStart(2, "0")}:00 ·{" "}
          {formatPrice(currentHourData.finalPrice)} €/kWh
         </div>
        ) : (
          <div style={homeStyles.infoText}>No disponible</div>
         )}
        </section>

        {/* ────────────────────────────── */}
        {/* ACTION CARD                   */}
        {/* ────────────────────────────── */}
        <section style={homeStyles.infoCard}>
          <div style={homeStyles.infoTitle}>Qué hacer hoy</div>
          <div style={homeStyles.infoText}>{premiumInsight.actionText}</div>
        </section>

        {/* ────────────────────────────── */}
        {/* WEATHER CARD                  */}
        {/* ────────────────────────────── */}
        <section style={homeStyles.infoCard}>
          <div style={homeStyles.infoTitle}>
            {weatherIcon} {weatherTitle}
          </div>
          <div style={homeStyles.infoText}>{weatherText}</div>
        </section>

        {/* ────────────────────────────── */}
        {/* METRICS                       */}
        {/* ────────────────────────────── */}
        <section style={homeStyles.metricsGrid}>
          <div style={homeStyles.metricCard}>
            <div style={homeStyles.metricLabel}>Media</div>
            <div style={homeStyles.metricValue}>
              {formatPrice(dayAnalysis.avg)}
            </div>
            <div style={homeStyles.metricUnit}>€/kWh</div>
          </div>

          <div style={homeStyles.metricCard}>
            <div style={homeStyles.metricLabel}>Hora más barata</div>
            <div style={homeStyles.metricValue}>
              {formatPrice(dayAnalysis.min)}
            </div>
            <div style={homeStyles.metricUnit}>€/kWh</div>
          </div>

          <div style={homeStyles.metricCard}>
            <div style={homeStyles.metricLabel}>Hora más cara</div>
            <div style={homeStyles.metricValue}>
              {formatPrice(dayAnalysis.max)}
            </div>
            <div style={homeStyles.metricUnit}>€/kWh</div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default Home;