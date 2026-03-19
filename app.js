const elements = {
  serviceStatus: document.getElementById("service-status"),
  currentStatus: document.getElementById("current-status"),
  currentTemperature: document.getElementById("current-temperature"),
  currentTempComparison: document.getElementById("current-temp-comparison"),
  currentTempComparisonDelta: document.getElementById("current-temp-comparison-delta"),
  currentTempComparisonText: document.getElementById("current-temp-comparison-text"),
  currentFeelsLike: document.getElementById("current-feels-like"),
  currentWind: document.getElementById("current-wind"),
  currentHumidity: document.getElementById("current-humidity"),
  currentRainChance: document.getElementById("current-rain-chance"),
  forecastList: document.getElementById("forecast-list"),
  analyticsAvgTemp: document.getElementById("analytics-avg-temp"),
  analyticsAvgTempDescription: document.getElementById("analytics-avg-temp-description"),
  analyticsAvgWindSpeed: document.getElementById("analytics-avg-wind-speed"),
  analyticsAvgWindDescription: document.getElementById("analytics-avg-wind-description"),
  analyticsPrecipDays: document.getElementById("analytics-precip-days"),
};

const WEATHER_DATA_URLS = ["/data/weather.json", "./data/weather.json"];
const ANALYTICS_DATA_URLS = ["/data/analytics.json", "./data/analytics.json"];
const WEATHER_AVERAGES_URLS = ["/data/weather_averages.json", "./data/weather_averages.json"];

const appState = {
  weather: null,
  weatherAverages: null,
};

function formatTimestamp(value) {
  if (!value) {
    return "Unavailable";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unavailable";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function formatDegrees(value) {
  return value == null ? "--" : `${value}`;
}

function formatSignedDegrees(value) {
  return value == null ? "--" : `${Math.abs(Math.round(value))}\u00b0`;
}

function formatCardValue(value, unit) {
  if (value == null) {
    return "--";
  }

  return unit ? `${value} ${unit}` : `${value}`;
}

function getAnalyticsCardValue(cards, cardId) {
  const match = cards.find((card) => card.id === cardId);
  return match && match.value != null ? match.value : null;
}

async function fetchJson(urls) {
  let lastError = null;

  for (const url of urls) {
    try {
      const response = await fetch(url, {
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Request failed with ${response.status} for ${url}`);
      }

      return await response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Unable to fetch JSON");
}

function renderForecast(days) {
  elements.forecastList.innerHTML = "";

  days.forEach((day) => {
    const item = document.createElement("div");
    item.className = "forecast-item";
    item.innerHTML = `
      <div>
        <strong>${day.label}</strong>
        <span>${day.summary}</span>
      </div>
      <p>${formatDegrees(day.highF)}&deg; / ${formatDegrees(day.lowF)}&deg;</p>
    `;
    elements.forecastList.appendChild(item);
  });
}

function getCurrentMonthAverage(monthlyAverages, dateValue) {
  if (!Array.isArray(monthlyAverages) || !dateValue) {
    return null;
  }

  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const monthNumber = date.getMonth() + 1;
  return monthlyAverages.find((entry) => entry.month_number === monthNumber) || null;
}

function getAnalyticsMonthAverage() {
  const comparisonDate =
    appState.weather?.current?.updatedAt ||
    appState.weather?.generatedAt ||
    new Date().toISOString();
  const monthlyAverages = appState.weatherAverages?.metrics?.by_month || [];
  return getCurrentMonthAverage(monthlyAverages, comparisonDate);
}

function renderTemperatureComparison() {
  const current = appState.weather?.current || null;
  const currentMonthAverage = getAnalyticsMonthAverage();
  const currentTemperature = current?.temperatureF;
  const averageTemperature = currentMonthAverage?.averages?.temperature;

  if (currentTemperature == null || averageTemperature == null || !currentMonthAverage?.month) {
    elements.currentTempComparison.hidden = true;
    delete elements.currentTempComparison.dataset.trend;
    elements.currentTempComparisonDelta.textContent = "--\u00b0";
    elements.currentTempComparisonText.textContent = "--";
    return;
  }

  const difference = Number((currentTemperature - averageTemperature).toFixed(1));
  const isAboveAverage = difference >= 0;
  const directionLabel = isAboveAverage ? "above" : "below";

  elements.currentTempComparison.hidden = false;
  elements.currentTempComparison.dataset.trend = isAboveAverage ? "above" : "below";
  elements.currentTempComparisonDelta.textContent = formatSignedDegrees(difference);
  elements.currentTempComparisonText.textContent = `${directionLabel} ${currentMonthAverage.month} average`;
}

function renderWeather(data) {
  const current = data.current || {};
  const wind = current.wind || {};

  elements.serviceStatus.textContent = `Weather generated ${formatTimestamp(data.generatedAt)}`;
  elements.serviceStatus.classList.remove("is-error");
  elements.currentStatus.textContent = current.summary || "Unavailable";
  elements.currentTemperature.innerHTML = `${formatDegrees(current.temperatureF)}&deg;`;
  elements.currentFeelsLike.innerHTML = `Feels like ${formatDegrees(current.feelsLikeF)}&deg;`;
  elements.currentWind.textContent = wind.label || "--";
  elements.currentHumidity.textContent = `${formatDegrees(current.humidityPercent)}%`;
  elements.currentRainChance.textContent = `${formatDegrees(current.rainChancePercent)}%`;
  renderForecast(data.forecast || []);
  appState.weather = data;
  renderTemperatureComparison();
  renderMonthlyAnalytics();
}

function renderAnalytics(data) {
  const cards = data.cards || [];
  elements.analyticsPrecipDays.textContent = formatCardValue(
    getAnalyticsCardValue(cards, "precip_days"),
    "days"
  );
}

function renderMonthlyAnalytics() {
  const currentMonthAverage = getAnalyticsMonthAverage();
  const monthLabel = currentMonthAverage?.month;
  const temperature = currentMonthAverage?.averages?.temperature;
  const windSpeed = currentMonthAverage?.averages?.wind_speed;

  elements.analyticsAvgTemp.textContent = formatCardValue(temperature, "F");
  elements.analyticsAvgWindSpeed.textContent = formatCardValue(windSpeed, "mph");

  elements.analyticsAvgTempDescription.textContent = monthLabel
    ? `${monthLabel} historical average`
    : "Historical average for this month";
  elements.analyticsAvgWindDescription.textContent = monthLabel
    ? `${monthLabel} historical average`
    : "Historical average for this month";
}

function renderError(message) {
  elements.serviceStatus.textContent = message;
  elements.serviceStatus.classList.add("is-error");
  elements.currentStatus.textContent = "Offline";
  elements.currentTemperature.innerHTML = "--&deg;";
  elements.currentTempComparison.hidden = true;
  delete elements.currentTempComparison.dataset.trend;
  elements.currentTempComparisonDelta.textContent = "--\u00b0";
  elements.currentTempComparisonText.textContent = "--";
  elements.currentFeelsLike.innerHTML = "Feels like --&deg;";
  elements.currentWind.textContent = "--";
  elements.currentHumidity.textContent = "--";
  elements.currentRainChance.textContent = "--";
  elements.forecastList.innerHTML = `
    <div class="forecast-item forecast-empty">
      <div>
        <strong>No data</strong>
        <span>Run the weather generator to populate /data/weather.json</span>
      </div>
      <p>--&deg; / --&deg;</p>
    </div>
  `;
}

function renderAnalyticsError() {
  elements.analyticsAvgTemp.textContent = "--";
  elements.analyticsAvgWindSpeed.textContent = "--";
  elements.analyticsPrecipDays.textContent = "--";
  elements.analyticsAvgTempDescription.textContent = "Historical average for this month";
  elements.analyticsAvgWindDescription.textContent = "Historical average for this month";
}

async function loadWeather() {
  try {
    const payload = await fetchJson(WEATHER_DATA_URLS);
    renderWeather(payload);
  } catch (error) {
    renderError("Unable to load generated weather data");
    console.error(error);
  }
}

async function loadWeatherAverages() {
  try {
    const payload = await fetchJson(WEATHER_AVERAGES_URLS);
    appState.weatherAverages = payload;
    renderTemperatureComparison();
    renderMonthlyAnalytics();
  } catch (error) {
    appState.weatherAverages = null;
    renderTemperatureComparison();
    renderMonthlyAnalytics();
    console.error(error);
  }
}

async function loadAnalytics() {
  try {
    const payload = await fetchJson(ANALYTICS_DATA_URLS);
    renderAnalytics(payload);
  } catch (error) {
    renderAnalyticsError();
    console.error(error);
  }
}

loadWeather();
loadWeatherAverages();
loadAnalytics();
renderMonthlyAnalytics();
