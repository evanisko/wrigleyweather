const elements = {
  serviceStatus: document.getElementById("service-status"),
  sourceLabel: document.getElementById("source-label"),
  currentStatus: document.getElementById("current-status"),
  currentTemperature: document.getElementById("current-temperature"),
  currentFeelsLike: document.getElementById("current-feels-like"),
  currentWind: document.getElementById("current-wind"),
  currentHumidity: document.getElementById("current-humidity"),
  currentRainChance: document.getElementById("current-rain-chance"),
  forecastList: document.getElementById("forecast-list"),
  analyticsAvgTemp: document.getElementById("analytics-avg-temp"),
  analyticsAvgWindSpeed: document.getElementById("analytics-avg-wind-speed"),
  analyticsPrecipDays: document.getElementById("analytics-precip-days"),
};

const WEATHER_DATA_URLS = ["/data/weather.json", "./data/weather.json"];
const ANALYTICS_DATA_URLS = ["/data/analytics.json", "./data/analytics.json"];

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

function renderWeather(data) {
  const current = data.current || {};
  const wind = current.wind || {};
  const source = data.source || {};

  elements.serviceStatus.textContent = `Weather generated ${formatTimestamp(data.generatedAt)}`;
  elements.serviceStatus.classList.remove("is-error");
  elements.sourceLabel.textContent = source.name || "Weather Source";
  elements.currentStatus.textContent = current.summary || "Unavailable";
  elements.currentTemperature.innerHTML = `${formatDegrees(current.temperatureF)}&deg;`;
  elements.currentFeelsLike.innerHTML = `Feels like ${formatDegrees(current.feelsLikeF)}&deg;`;
  elements.currentWind.textContent = wind.label || "--";
  elements.currentHumidity.textContent = `${formatDegrees(current.humidityPercent)}%`;
  elements.currentRainChance.textContent = `${formatDegrees(current.rainChancePercent)}%`;
  renderForecast(data.forecast || []);
}

function renderAnalytics(data) {
  const cards = data.cards || [];
  elements.analyticsAvgTemp.textContent = formatCardValue(
    getAnalyticsCardValue(cards, "avg_temp"),
    "F"
  );
  elements.analyticsAvgWindSpeed.textContent = formatCardValue(
    getAnalyticsCardValue(cards, "avg_wind_speed"),
    "mph"
  );
  elements.analyticsPrecipDays.textContent = formatCardValue(
    getAnalyticsCardValue(cards, "precip_days"),
    "days"
  );
}

function renderError(message) {
  elements.serviceStatus.textContent = message;
  elements.serviceStatus.classList.add("is-error");
  elements.currentStatus.textContent = "Offline";
  elements.currentTemperature.innerHTML = "--&deg;";
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
loadAnalytics();
