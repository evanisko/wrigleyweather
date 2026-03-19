const elements = {
  updatedAt: document.getElementById("updated-at"),
  serviceStatus: document.getElementById("service-status"),
  sourceLabel: document.getElementById("source-label"),
  currentStatus: document.getElementById("current-status"),
  currentTemperature: document.getElementById("current-temperature"),
  currentFeelsLike: document.getElementById("current-feels-like"),
  currentHeatIndex: document.getElementById("current-heat-index"),
  currentWindChill: document.getElementById("current-wind-chill"),
  currentWind: document.getElementById("current-wind"),
  currentHumidity: document.getElementById("current-humidity"),
  currentRainChance: document.getElementById("current-rain-chance"),
  currentComfort: document.getElementById("current-comfort"),
  forecastList: document.getElementById("forecast-list"),
  analyticsAvgTemp: document.getElementById("analytics-avg-temp"),
  analyticsAvgWindSpeed: document.getElementById("analytics-avg-wind-speed"),
  analyticsPrecipDays: document.getElementById("analytics-precip-days"),
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

function formatCardValue(value, unit) {
  if (value == null) {
    return "--";
  }

  return unit ? `${value} ${unit}` : `${value}`;
}

function getAnalyticsCardValue(cards, cardId) {
  return cards.find((card) => card.id === cardId)?.value ?? null;
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
  elements.updatedAt.textContent = formatTimestamp(data.current.updatedAt);
  elements.serviceStatus.textContent = `Weather generated ${formatTimestamp(data.generatedAt)}`;
  elements.serviceStatus.classList.remove("is-error");
  elements.sourceLabel.textContent = data.source.name;
  elements.currentStatus.textContent = data.current.summary || "Unavailable";
  elements.currentTemperature.innerHTML = `${formatDegrees(data.current.temperatureF)}&deg;`;
  elements.currentFeelsLike.innerHTML = `Feels like ${formatDegrees(data.current.feelsLikeF)}&deg;`;
  elements.currentHeatIndex.innerHTML = `${formatDegrees(data.current.heatIndexF)}&deg;`;
  elements.currentWindChill.innerHTML = `${formatDegrees(data.current.windChillF)}&deg;`;
  elements.currentWind.textContent = data.current.wind.label || "--";
  elements.currentHumidity.textContent = `${formatDegrees(data.current.humidityPercent)}%`;
  elements.currentRainChance.textContent = `${formatDegrees(data.current.rainChancePercent)}%`;
  elements.currentComfort.textContent = data.current.comfort || "--";
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
  elements.updatedAt.textContent = "Unavailable";
  elements.currentStatus.textContent = "Offline";
  elements.currentTemperature.innerHTML = "--&deg;";
  elements.currentFeelsLike.innerHTML = "Feels like --&deg;";
  elements.currentHeatIndex.innerHTML = "--&deg;";
  elements.currentWindChill.innerHTML = "--&deg;";
  elements.currentWind.textContent = "--";
  elements.currentHumidity.textContent = "--";
  elements.currentRainChance.textContent = "--";
  elements.currentComfort.textContent = "--";
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
    const response = await fetch("./data/weather.json", {
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Weather request failed with ${response.status}`);
    }

    const payload = await response.json();
    renderWeather(payload);
  } catch (error) {
    renderError("Unable to load generated weather data");
    console.error(error);
  }
}

async function loadAnalytics() {
  try {
    const response = await fetch("./data/analytics.json", {
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Analytics request failed with ${response.status}`);
    }

    const payload = await response.json();
    renderAnalytics(payload);
  } catch (error) {
    renderAnalyticsError();
    console.error(error);
  }
}

loadWeather();
loadAnalytics();
