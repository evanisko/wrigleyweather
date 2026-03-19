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

loadWeather();
