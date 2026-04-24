export const tariffConfig = {
  regulatedCosts2026: {
    peajes: {
      P1: 0.033261,
      P2: 0.016409,
      P3: 0.000077,
    },
    cargos: {
      P1: 0.064292,
      P2: 0.012858,
      P3: 0.003215,
    },
  },

  extraCostsPerKwh: {
    comercializadora: 0,
    desvios: 0,
  },

  valleySpecialDates: [
    "2026-01-06",
  ],
};

export function isValleyDay(dateIso) {
  if (!dateIso) return false;

  if (tariffConfig.valleySpecialDates.includes(dateIso)) {
    return true;
  }

  const date = new Date(`${dateIso}T12:00:00`);
  const day = date.getDay();

  return day === 0 || day === 6;
}

export function getTariffPeriod(dateIso, hour) {
  if (isValleyDay(dateIso)) {
    return "P3";
  }

  const startHour = Number(hour) - 1;

  if (startHour >= 0 && startHour < 8) {
    return "P3";
  }

  if (
    (startHour >= 8 && startHour < 10) ||
    (startHour >= 14 && startHour < 18) ||
    (startHour >= 22 && startHour < 24)
  ) {
    return "P2";
  }

  return "P1";
}

export function getRegulatedCostPerKwh(period) {
  const peaje = tariffConfig.regulatedCosts2026.peajes[period] ?? 0;
  const cargo = tariffConfig.regulatedCosts2026.cargos[period] ?? 0;

  return peaje + cargo;
}

export function getExtraCostPerKwh() {
  const { comercializadora, desvios } = tariffConfig.extraCostsPerKwh;
  return comercializadora + desvios;
}

export function getSystemCostPerKwh(dateIso, hour) {
  const period = getTariffPeriod(dateIso, hour);
  return getRegulatedCostPerKwh(period) + getExtraCostPerKwh();
}

export function calculateFinalPricePerKwh(omiePrice, dateIso, hour) {
  return Number(omiePrice) + getSystemCostPerKwh(dateIso, hour);
}