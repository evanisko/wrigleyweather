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
  analyticsSimilarRuns: document.getElementById("analytics-similar-runs"),
  analyticsSimilarRunsDescription: document.getElementById("analytics-similar-runs-description"),
  analyticsSimilarHomeRuns: document.getElementById("analytics-similar-home-runs"),
  analyticsSimilarHomeRunsDescription: document.getElementById(
    "analytics-similar-home-runs-description"
  ),
  analyticsSimilarGameDuration: document.getElementById("analytics-similar-game-duration"),
  analyticsSimilarGameDurationDescription: document.getElementById(
    "analytics-similar-game-duration-description"
  ),
  analyticsAvgRuns: document.getElementById("analytics-avg-runs"),
  analyticsAvgRunsDescription: document.getElementById("analytics-avg-runs-description"),
  analyticsAvgHomeRuns: document.getElementById("analytics-avg-home-runs"),
  analyticsAvgHomeRunsDescription: document.getElementById("analytics-avg-home-runs-description"),
  analyticsAvgGameDuration: document.getElementById("analytics-avg-game-duration"),
  analyticsAvgGameDurationDescription: document.getElementById(
    "analytics-avg-game-duration-description"
  ),
};

const WEATHER_DATA_URLS = ["/data/weather.json", "./data/weather.json"];
const WEATHER_AVERAGES_URLS = ["/data/weather_averages.json", "./data/weather_averages.json"];
const BALL_AVERAGES_URLS = ["/data/ball_averages.json", "./data/ball_averages.json"];
const FORECAST_SIMILARITY_URLS = [
  "/data/forecast_similarity.json",
  "./data/forecast_similarity.json",
];

const appState = {
  weather: null,
  weatherAverages: null,
  ballAverages: null,
  forecastSimilarity: null,
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

function formatDifference(value, unit) {
  if (value == null) {
    return "--";
  }

  const rounded = Number(value.toFixed(1));
  const absolute = Math.abs(rounded);
  return unit ? `${absolute} ${unit}` : `${absolute}`;
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

function getBaseballMonthAverage() {
  const comparisonDate =
    appState.weather?.current?.updatedAt ||
    appState.weather?.generatedAt ||
    new Date().toISOString();
  const monthlyAverages = appState.ballAverages?.metrics?.by_month || [];
  return getCurrentMonthAverage(monthlyAverages, comparisonDate);
}

function buildComparisonLabel(similarValue, monthlyValue, monthLabel, unit) {
  if (similarValue == null || monthlyValue == null || !monthLabel) {
    return "Compared with this month's average";
  }

  const difference = similarValue - monthlyValue;
  const direction = difference >= 0 ? "above" : "below";
  return `${formatDifference(difference, unit)} ${direction} ${monthLabel} average`;
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
  renderBallparkAnalytics();
}

function renderBallparkAnalytics() {
  const currentMonthAverage = getBaseballMonthAverage();
  const monthLabel = currentMonthAverage?.month;
  const runs = currentMonthAverage?.averages?.runs;
  const homeRuns = currentMonthAverage?.averages?.home_runs;
  const gameDuration = currentMonthAverage?.averages?.game_time_minutes;
  const similarResults = appState.forecastSimilarity?.results || null;
  const similarRuns = similarResults?.averages?.runs;
  const similarHomeRuns = similarResults?.averages?.home_runs;
  const similarGameDuration = similarResults?.averages?.game_time_minutes;
  const matchedGameCount = similarResults?.matched_game_count;

  elements.analyticsSimilarRuns.textContent = formatCardValue(similarRuns, null);
  elements.analyticsSimilarHomeRuns.textContent = formatCardValue(similarHomeRuns, null);
  elements.analyticsSimilarGameDuration.textContent = formatCardValue(similarGameDuration, "min");

  elements.analyticsSimilarRunsDescription.textContent =
    matchedGameCount > 0
      ? `${buildComparisonLabel(similarRuns, runs, monthLabel, null)} from ${matchedGameCount} similar games`
      : "No similar games found";
  elements.analyticsSimilarHomeRunsDescription.textContent =
    matchedGameCount > 0
      ? `${buildComparisonLabel(similarHomeRuns, homeRuns, monthLabel, null)} from ${matchedGameCount} similar games`
      : "No similar games found";
  elements.analyticsSimilarGameDurationDescription.textContent =
    matchedGameCount > 0
      ? `${buildComparisonLabel(similarGameDuration, gameDuration, monthLabel, "min")} from ${matchedGameCount} similar games`
      : "No similar games found";

  elements.analyticsAvgRuns.textContent = formatCardValue(runs, null);
  elements.analyticsAvgHomeRuns.textContent = formatCardValue(homeRuns, null);
  elements.analyticsAvgGameDuration.textContent = formatCardValue(gameDuration, "min");

  elements.analyticsAvgRunsDescription.textContent = monthLabel
    ? `${monthLabel} historical average`
    : "Historical average for this month";
  elements.analyticsAvgHomeRunsDescription.textContent = monthLabel
    ? `${monthLabel} historical average`
    : "Historical average for this month";
  elements.analyticsAvgGameDurationDescription.textContent = monthLabel
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

function renderBallparkAnalyticsError() {
  elements.analyticsSimilarRuns.textContent = "--";
  elements.analyticsSimilarHomeRuns.textContent = "--";
  elements.analyticsSimilarGameDuration.textContent = "--";
  elements.analyticsAvgRuns.textContent = "--";
  elements.analyticsAvgHomeRuns.textContent = "--";
  elements.analyticsAvgGameDuration.textContent = "--";
  elements.analyticsSimilarRunsDescription.textContent = "Compared with this month's average";
  elements.analyticsSimilarHomeRunsDescription.textContent =
    "Compared with this month's average";
  elements.analyticsSimilarGameDurationDescription.textContent =
    "Compared with this month's average";
  elements.analyticsAvgRunsDescription.textContent = "Historical average for this month";
  elements.analyticsAvgHomeRunsDescription.textContent = "Historical average for this month";
  elements.analyticsAvgGameDurationDescription.textContent =
    "Historical average for this month";
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
    renderBallparkAnalytics();
  } catch (error) {
    appState.weatherAverages = null;
    renderTemperatureComparison();
    renderBallparkAnalytics();
    console.error(error);
  }
}

async function loadBallAverages() {
  try {
    const payload = await fetchJson(BALL_AVERAGES_URLS);
    appState.ballAverages = payload;
    renderBallparkAnalytics();
  } catch (error) {
    appState.ballAverages = null;
    renderBallparkAnalyticsError();
    console.error(error);
  }
}

async function loadForecastSimilarity() {
  try {
    const payload = await fetchJson(FORECAST_SIMILARITY_URLS);
    appState.forecastSimilarity = payload;
    renderBallparkAnalytics();
  } catch (error) {
    appState.forecastSimilarity = null;
    renderBallparkAnalytics();
    console.error(error);
  }
}

loadWeather();
loadWeatherAverages();
loadBallAverages();
loadForecastSimilarity();
renderBallparkAnalytics();
