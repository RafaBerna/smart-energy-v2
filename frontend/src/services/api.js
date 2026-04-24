// frontend/src/services/api.js

const BASE_URL = "http://localhost:8000";

async function fetchJson(url, errorMessage) {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(errorMessage);
  }

  const data = await response.json();

  if (data?.error) {
    throw new Error(data.error);
  }

  return data;
}

// --- ENDPOINTS HOME / ÚLTIMO DISPONIBLE ---

export function fetchLatestPriceDay() {
  return fetchJson(
    `${BASE_URL}/price-day/latest`,
    "No se pudo cargar el último día"
  );
}

export function fetchLatestHours() {
  return fetchJson(
    `${BASE_URL}/price-hours/latest`,
    "No se pudieron cargar las últimas horas disponibles"
  );
}

export function fetchLatestPeriods() {
  return fetchJson(
    `${BASE_URL}/price-periods/latest`,
    "No se pudieron cargar los últimos periodos disponibles"
  );
}

// --- ENDPOINTS TODAY ---

export function fetchTodayPriceDay() {
  return fetchJson(
    `${BASE_URL}/price-day/today`,
    "No se pudo cargar el día de hoy"
  );
}

export function fetchTodayHours() {
  return fetchJson(
    `${BASE_URL}/price-hours/today`,
    "No se pudieron cargar las horas de hoy"
  );
}

export function fetchTodayPeriods() {
  return fetchJson(
    `${BASE_URL}/price-periods/today`,
    "No se pudieron cargar los periodos de hoy"
  );
}

// --- WEATHER ---

export function fetchWeatherByLocation(location) {
  return fetchJson(
    `${BASE_URL}/weather/by-location?location=${encodeURIComponent(location)}`,
    "No se pudo cargar la meteorología"
  );
}

// --- ENDPOINTS BY DATE ---

export function fetchHoursByDate(date) {
  return fetchJson(
    `${BASE_URL}/price-hours/by-date?date=${encodeURIComponent(date)}`,
    "No se pudieron cargar las horas por fecha"
  );
}

export function fetchPeriodsByDate(date) {
  return fetchJson(
    `${BASE_URL}/price-periods/by-date?date=${encodeURIComponent(date)}`,
    "No se pudieron cargar los periodos por fecha"
  );
}

// --- ENDPOINT HISTORY ---

export function fetchPriceDaysHistory(limit = 30) {
  return fetchJson(
    `${BASE_URL}/price-days/history?limit=${limit}`,
    "No se pudo cargar el histórico de precios"
  );
}