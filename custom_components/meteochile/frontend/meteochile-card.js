/**
 * MeteoChile Card — tarjeta de Home Assistant para la integración meteochile-ha.
 * Muestra la condición actual, el índice UV, el detalle de la estación y el
 * pronóstico de la Dirección Meteorológica de Chile. Incluye editor visual.
 *
 * Se distribuye junto con la integración y se carga sola en el frontend.
 */

const CARD_VERSION = "0.2.0";

const ICONS = {
  "clear-night": "mdi:weather-night",
  cloudy: "mdi:weather-cloudy",
  exceptional: "mdi:alert-circle-outline",
  fog: "mdi:weather-fog",
  hail: "mdi:weather-hail",
  lightning: "mdi:weather-lightning",
  "lightning-rainy": "mdi:weather-lightning-rainy",
  partlycloudy: "mdi:weather-partly-cloudy",
  pouring: "mdi:weather-pouring",
  rainy: "mdi:weather-rainy",
  snowy: "mdi:weather-snowy",
  "snowy-rainy": "mdi:weather-snowy-rainy",
  sunny: "mdi:weather-sunny",
  windy: "mdi:weather-windy",
  "windy-variant": "mdi:weather-windy-variant",
};

const NIGHT_ICONS = {
  partlycloudy: "mdi:weather-night-partly-cloudy",
  sunny: "mdi:weather-night",
};

const CONDITION_ES = {
  "clear-night": "Despejado",
  cloudy: "Nublado",
  exceptional: "Excepcional",
  fog: "Niebla",
  hail: "Granizo",
  lightning: "Tormenta eléctrica",
  "lightning-rainy": "Tormenta con lluvia",
  partlycloudy: "Parcialmente nublado",
  pouring: "Lluvia intensa",
  rainy: "Lluvia",
  snowy: "Nieve",
  "snowy-rainy": "Aguanieve",
  sunny: "Despejado",
  windy: "Viento",
  "windy-variant": "Viento y nubes",
};

const STRINGS = {
  es: {
    humidity: "Humedad",
    wind: "Viento",
    visibility: "Visibilidad",
    uv: "UV",
    station: "Estación",
    observed: "obs.",
    today: "Hoy",
    tonight: "Noche",
    day: "Día",
    issued: "Pronóstico emitido",
    no_entity: "Selecciona una entidad de MeteoChile en la configuración de la tarjeta.",
    not_found: "Entidad no encontrada",
    unavailable: "No disponible",
    uv_levels: ["Bajo", "Moderado", "Alto", "Muy alto", "Extremo"],
    periods: { madrugada: "Madrugada", "mañana": "Mañana", tarde: "Tarde", noche: "Noche" },
    card_name: "MeteoChile",
    card_description: "Clima actual y pronóstico de la Dirección Meteorológica de Chile.",
  },
  en: {
    humidity: "Humidity",
    wind: "Wind",
    visibility: "Visibility",
    uv: "UV",
    station: "Station",
    observed: "obs.",
    today: "Today",
    tonight: "Night",
    day: "Day",
    issued: "Forecast issued",
    no_entity: "Pick a MeteoChile entity in the card configuration.",
    not_found: "Entity not found",
    unavailable: "Unavailable",
    uv_levels: ["Low", "Moderate", "High", "Very high", "Extreme"],
    periods: { madrugada: "Early morning", "mañana": "Morning", tarde: "Afternoon", noche: "Night" },
    card_name: "MeteoChile",
    card_description: "Current weather and forecast from the Chilean Meteorological Directorate.",
  },
};

const EDITOR_LABELS = {
  es: {
    entity: "Localidad (entidad weather de MeteoChile)",
    name: "Título (opcional)",
    show_current: "Mostrar condición actual",
    show_details: "Mostrar humedad, viento y visibilidad",
    show_uv: "Mostrar índice UV",
    show_station: "Mostrar estación y hora de observación",
    show_forecast: "Mostrar pronóstico",
    forecast_type: "Tipo de pronóstico",
    days: "Días de pronóstico",
    show_text: "Mostrar texto del pronóstico de hoy (por tramo)",
    show_issued: "Mostrar hora de emisión del pronóstico",
    daily: "Diario",
    twice_daily: "Día y noche",
    sections: "Secciones",
    forecast: "Pronóstico",
  },
  en: {
    entity: "Location (MeteoChile weather entity)",
    name: "Title (optional)",
    show_current: "Show current conditions",
    show_details: "Show humidity, wind and visibility",
    show_uv: "Show UV index",
    show_station: "Show station and observation time",
    show_forecast: "Show forecast",
    forecast_type: "Forecast type",
    days: "Forecast days",
    show_text: "Show today's forecast text (by period)",
    show_issued: "Show forecast issue time",
    daily: "Daily",
    twice_daily: "Day and night",
    sections: "Sections",
    forecast: "Forecast",
  },
};

const DEFAULTS = {
  show_current: true,
  show_details: true,
  show_uv: true,
  show_station: true,
  show_forecast: true,
  forecast_type: "daily",
  days: 5,
  show_text: false,
  show_issued: false,
};

const lang = (hass) => ((hass && hass.language) || "es").toLowerCase().startsWith("es") ? "es" : "en";
const t = (hass) => STRINGS[lang(hass)];

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fmtNumber = (value, digits = 0) =>
  value === undefined || value === null || value === "" || Number.isNaN(Number(value))
    ? null
    : Number(value).toLocaleString("es-CL", { maximumFractionDigits: digits, minimumFractionDigits: 0 });

const CARDINALS_ES = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"];
const CARDINALS_EN = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

function cardinal(bearing, hass) {
  if (bearing === undefined || bearing === null || bearing === "") return null;
  const list = lang(hass) === "es" ? CARDINALS_ES : CARDINALS_EN;
  return list[Math.round(((Number(bearing) % 360) / 22.5)) % 16];
}

function uvLevel(uv, hass) {
  const levels = t(hass).uv_levels;
  if (uv < 3) return { label: levels[0], color: "#3ea72d" };
  if (uv < 6) return { label: levels[1], color: "#fff300" };
  if (uv < 8) return { label: levels[2], color: "#f18b00" };
  if (uv < 11) return { label: levels[3], color: "#e53210" };
  return { label: levels[4], color: "#b567a4" };
}

function conditionLabel(hass, stateObj) {
  if (hass && typeof hass.formatEntityState === "function") {
    try {
      const text = hass.formatEntityState(stateObj);
      if (text && text !== stateObj.state) return text;
    } catch (_err) {
      /* sigue con el mapa propio */
    }
  }
  return CONDITION_ES[stateObj.state] || stateObj.state;
}

function conditionIcon(condition, night = false) {
  if (night && NIGHT_ICONS[condition]) return NIGHT_ICONS[condition];
  return ICONS[condition] || "mdi:weather-cloudy-alert";
}

function dayLabel(iso, hass, index, forecastType, isDaytime) {
  const s = t(hass);
  const date = new Date(iso);
  const today = new Date();
  const sameDay =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate();
  if (forecastType === "twice_daily") {
    if (isDaytime === false) return s.tonight;
    return sameDay ? s.today : date.toLocaleDateString(lang(hass) === "es" ? "es-CL" : "en-US", { weekday: "short" });
  }
  if (sameDay) return s.today;
  return date.toLocaleDateString(lang(hass) === "es" ? "es-CL" : "en-US", { weekday: "short", day: "numeric" });
}

// ---------------------------------------------------------------------------
// Tarjeta
// ---------------------------------------------------------------------------

class MeteoChileCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._forecast = null;
    this._unsub = null;
    this._subKey = null;
  }

  static getConfigElement() {
    return document.createElement("meteochile-card-editor");
  }

  static getStubConfig(hass) {
    const entity =
      Object.keys(hass.states).find((id) => id.startsWith("weather.meteochile")) ||
      Object.keys(hass.states).find(
        (id) => id.startsWith("weather.") && String(hass.states[id].attributes.attribution || "").includes("Meteorológica de Chile")
      ) ||
      "";
    return { entity };
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    const days = Number(config.days ?? DEFAULTS.days);
    this._config = { ...DEFAULTS, ...config, days: Math.min(Math.max(Number.isFinite(days) ? days : 5, 1), 10) };
    this._resubscribe();
    this._render();
  }

  set hass(hass) {
    const prev = this._hass;
    this._hass = hass;
    if (!prev || prev.connection !== hass.connection) this._resubscribe();
    const id = this._config && this._config.entity;
    if (!prev || !id || prev.states[id] !== hass.states[id] || prev.language !== hass.language) {
      this._render();
    }
  }

  connectedCallback() {
    this._resubscribe();
  }

  disconnectedCallback() {
    this._unsubscribe();
  }

  getCardSize() {
    const c = this._config || DEFAULTS;
    let size = 1;
    if (c.show_current) size += 2;
    if (c.show_details) size += 1;
    if (c.show_forecast) size += 2;
    if (c.show_text) size += 2;
    return size;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  _unsubscribe() {
    if (this._unsub) {
      const unsub = this._unsub;
      this._unsub = null;
      Promise.resolve(unsub)
        .then((fn) => typeof fn === "function" && fn())
        .catch(() => {});
    }
    this._subKey = null;
  }

  _resubscribe() {
    const hass = this._hass;
    const config = this._config;
    if (!hass || !config || !this.isConnected) return;
    const key = config.show_forecast && config.entity ? `${config.entity}|${config.forecast_type}` : null;
    if (key === this._subKey) return;
    this._unsubscribe();
    this._forecast = null;
    if (!key) return;
    this._subKey = key;
    try {
      this._unsub = hass.connection.subscribeMessage(
        (msg) => {
          this._forecast = msg.forecast || [];
          this._render();
        },
        { type: "weather/subscribe_forecast", entity_id: config.entity, forecast_type: config.forecast_type }
      );
      Promise.resolve(this._unsub).catch((err) => {
        console.warn("meteochile-card: no se pudo obtener el pronóstico", err);
        this._forecast = [];
        this._render();
      });
    } catch (err) {
      console.warn("meteochile-card: no se pudo obtener el pronóstico", err);
    }
  }

  _render() {
    if (!this._config) return;
    const hass = this._hass;
    const s = t(hass);
    const c = this._config;

    if (!hass) return;
    if (!c.entity) {
      this._paint(`<div class="warning">${escapeHtml(s.no_entity)}</div>`);
      return;
    }
    const stateObj = hass.states[c.entity];
    if (!stateObj) {
      this._paint(`<div class="warning">${escapeHtml(s.not_found)}: ${escapeHtml(c.entity)}</div>`);
      return;
    }
    if (stateObj.state === "unavailable" || stateObj.state === "unknown") {
      this._paint(`<div class="warning">${escapeHtml(c.name || stateObj.attributes.friendly_name || c.entity)}: ${escapeHtml(s.unavailable)}</div>`);
      return;
    }

    const a = stateObj.attributes;
    const unit = a.temperature_unit || "°C";
    const title = c.name || a.localidad || a.friendly_name || c.entity;
    const isNight = stateObj.state === "clear-night" || (hass.states["sun.sun"] && hass.states["sun.sun"].state === "below_horizon");

    const parts = [];

    // ---- encabezado / actual
    if (c.show_current) {
      const temp = fmtNumber(a.temperature, 1);
      let uvHtml = "";
      if (c.show_uv && a.uv_index !== undefined && a.uv_index !== null) {
        const lvl = uvLevel(Number(a.uv_index), hass);
        const uvText = Number(a.uv_index) >= 11 ? "11+" : fmtNumber(a.uv_index);
        uvHtml = `<span class="uv" style="--uv-color:${lvl.color}" title="${escapeHtml(lvl.label)}">${s.uv} ${uvText} · ${escapeHtml(lvl.label)}</span>`;
      }
      parts.push(`
        <div class="current">
          <ha-icon class="big-icon" icon="${conditionIcon(stateObj.state, isNight)}"></ha-icon>
          <div class="main">
            <div class="title">${escapeHtml(title)}</div>
            <div class="condition">${escapeHtml(conditionLabel(hass, stateObj))}</div>
            ${uvHtml}
          </div>
          <div class="temp">${temp !== null ? `${temp}<span class="unit">${escapeHtml(unit)}</span>` : "—"}</div>
        </div>`);
    } else {
      parts.push(`<div class="title solo">${escapeHtml(title)}</div>`);
    }

    // ---- detalles
    if (c.show_details) {
      const items = [];
      const hum = fmtNumber(a.humidity);
      if (hum !== null) items.push(["mdi:water-percent", s.humidity, `${hum} %`]);
      const ws = fmtNumber(a.wind_speed, 1);
      if (ws !== null) {
        const dir = cardinal(a.wind_bearing, hass);
        items.push(["mdi:weather-windy", s.wind, `${ws} ${escapeHtml(a.wind_speed_unit || "km/h")}${dir ? ` ${dir}` : ""}`]);
      }
      const vis = fmtNumber(a.visibility, 1);
      if (vis !== null) items.push(["mdi:eye-outline", s.visibility, `${vis} ${escapeHtml(a.visibility_unit || "km")}`]);
      if (items.length) {
        parts.push(`<div class="details">${items
          .map(([icon, label, value]) => `<div class="detail"><ha-icon icon="${icon}"></ha-icon><span class="label">${escapeHtml(label)}</span><span class="value">${value}</span></div>`)
          .join("")}</div>`);
      }
    }

    // ---- estación
    if (c.show_station && a.estacion) {
      const obs = a.hora_observacion ? ` · ${s.observed} ${escapeHtml(a.hora_observacion)}` : "";
      parts.push(`<div class="meta"><ha-icon icon="mdi:radio-tower"></ha-icon>${escapeHtml(s.station)}: ${escapeHtml(a.estacion)}${obs}</div>`);
    }

    // ---- pronóstico
    if (c.show_forecast) {
      const fc = this._forecast;
      if (fc && fc.length) {
        const limit = c.forecast_type === "twice_daily" ? c.days * 2 : c.days;
        const items = fc.slice(0, limit);
        parts.push(`<div class="forecast ${c.forecast_type}">${items
          .map((f, i) => {
            const hi = fmtNumber(f.temperature);
            const lo = fmtNumber(f.templow);
            const night = f.is_daytime === false;
            return `<div class="fday${night ? " night" : ""}">
              <div class="fname">${escapeHtml(dayLabel(f.datetime, hass, i, c.forecast_type, f.is_daytime))}</div>
              <ha-icon icon="${conditionIcon(f.condition, night)}" title="${escapeHtml(CONDITION_ES[f.condition] || f.condition || "")}"></ha-icon>
              <div class="ftemp">${hi !== null ? `<span class="hi">${hi}°</span>` : ""}${lo !== null ? `<span class="lo">${lo}°</span>` : ""}</div>
            </div>`;
          })
          .join("")}</div>`);
      } else if (fc === null) {
        parts.push(`<div class="forecast loading"></div>`);
      }
    }

    // ---- texto del pronóstico de hoy
    if (c.show_text && a.pronostico_hoy && typeof a.pronostico_hoy === "object") {
      const rows = Object.entries(a.pronostico_hoy)
        .filter(([, text]) => text)
        .map(([period, text]) => `<div class="trow"><span class="tperiod">${escapeHtml(s.periods[period] || period)}</span><span>${escapeHtml(text)}</span></div>`);
      if (rows.length) parts.push(`<div class="text">${rows.join("")}</div>`);
    }

    if (c.show_issued && a.pronostico_redactado) {
      parts.push(`<div class="meta small">${escapeHtml(s.issued)}: ${escapeHtml(a.pronostico_redactado)}</div>`);
    }

    if (a.attribution) {
      parts.push(`<div class="attribution">${escapeHtml(a.attribution)}</div>`);
    }

    this._paint(parts.join(""));
  }

  _paint(inner) {
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="card">${inner}</div></ha-card>`;
    const card = this.shadowRoot.querySelector("ha-card");
    if (card && this._config && this._config.entity) {
      card.addEventListener("click", (ev) => {
        if (ev.target.closest && ev.target.closest("a")) return;
        const event = new Event("hass-more-info", { bubbles: true, composed: true });
        event.detail = { entityId: this._config.entity };
        this.dispatchEvent(event);
      });
    }
  }
}

const STYLE = `
  :host { display: block; }
  ha-card { cursor: pointer; height: 100%; }
  .card { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .warning { padding: 8px; color: var(--warning-color, #f57c00); }
  .current { display: flex; align-items: center; gap: 12px; }
  .big-icon { --mdc-icon-size: 56px; color: var(--state-icon-color, var(--primary-color)); flex: none; }
  .main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .title { font-size: 1.2em; font-weight: 500; color: var(--primary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .title.solo { font-size: 1.1em; }
  .condition { color: var(--secondary-text-color); }
  .temp { font-size: 2.6em; font-weight: 300; line-height: 1; color: var(--primary-text-color); white-space: nowrap; }
  .temp .unit { font-size: 0.45em; vertical-align: top; margin-left: 2px; color: var(--secondary-text-color); }
  .uv { align-self: flex-start; margin-top: 4px; font-size: 0.8em; padding: 2px 8px; border-radius: 10px;
        background: color-mix(in srgb, var(--uv-color) 25%, transparent); border: 1px solid var(--uv-color);
        color: var(--primary-text-color); }
  .details { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; }
  .detail { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 6px; align-items: center; }
  .detail ha-icon { grid-row: span 2; --mdc-icon-size: 22px; color: var(--secondary-text-color); }
  .detail .label { font-size: 0.75em; color: var(--secondary-text-color); }
  .detail .value { font-size: 0.95em; color: var(--primary-text-color); }
  .meta { display: flex; align-items: center; gap: 6px; font-size: 0.8em; color: var(--secondary-text-color); }
  .meta ha-icon { --mdc-icon-size: 16px; }
  .meta.small { font-size: 0.75em; }
  .forecast { display: flex; justify-content: space-between; gap: 4px; border-top: 1px solid var(--divider-color); padding-top: 12px; }
  .forecast.loading { min-height: 84px; }
  .fday { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 4px; }
  .fday.night { opacity: 0.8; }
  .fname { font-size: 0.8em; color: var(--secondary-text-color); text-transform: capitalize; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .fday ha-icon { --mdc-icon-size: 30px; color: var(--state-icon-color, var(--primary-color)); }
  .ftemp { display: flex; gap: 6px; font-size: 0.9em; }
  .ftemp .hi { color: var(--primary-text-color); font-weight: 500; }
  .ftemp .lo { color: var(--secondary-text-color); }
  .text { display: flex; flex-direction: column; gap: 4px; border-top: 1px solid var(--divider-color); padding-top: 12px; font-size: 0.85em; color: var(--primary-text-color); }
  .trow { display: grid; grid-template-columns: 90px 1fr; gap: 8px; }
  .tperiod { color: var(--secondary-text-color); }
  .attribution { font-size: 0.7em; color: var(--secondary-text-color); opacity: 0.8; text-align: right; }
`;

// ---------------------------------------------------------------------------
// Editor visual
// ---------------------------------------------------------------------------

class MeteoChileCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else this._render();
  }

  _labels() {
    return EDITOR_LABELS[lang(this._hass)];
  }

  _schema() {
    const l = this._labels();
    return [
      { name: "entity", required: true, selector: { entity: { domain: "weather", integration: "meteochile" } } },
      { name: "name", selector: { text: {} } },
      {
        type: "expandable",
        name: "",
        title: l.sections,
        icon: "mdi:view-list",
        expanded: true,
        schema: [
          { name: "show_current", selector: { boolean: {} } },
          { name: "show_uv", selector: { boolean: {} } },
          { name: "show_details", selector: { boolean: {} } },
          { name: "show_station", selector: { boolean: {} } },
          { name: "show_text", selector: { boolean: {} } },
          { name: "show_issued", selector: { boolean: {} } },
        ],
      },
      {
        type: "expandable",
        name: "",
        title: l.forecast,
        icon: "mdi:calendar-range",
        expanded: true,
        schema: [
          { name: "show_forecast", selector: { boolean: {} } },
          {
            name: "forecast_type",
            selector: {
              select: {
                mode: "dropdown",
                options: [
                  { value: "daily", label: l.daily },
                  { value: "twice_daily", label: l.twice_daily },
                ],
              },
            },
          },
          { name: "days", selector: { number: { min: 1, max: 5, step: 1, mode: "slider" } } },
        ],
      },
    ];
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => this._labels()[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        const value = { ...ev.detail.value };
        // No guardar valores iguales al predeterminado: YAML más limpio.
        for (const [key, def] of Object.entries(DEFAULTS)) {
          if (value[key] === def) delete value[key];
        }
        if (!value.name) delete value.name;
        const { entity, ...rest } = value;
        this._config = { type: this._config.type, entity, ...rest };
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { ...DEFAULTS, ...this._config };
    this._form.schema = this._schema();
  }
}

// El frontend de Home Assistant instala su propio registro de elementos
// (polyfill de registros con ámbito). Si la tarjeta se define antes de que
// eso ocurra, queda en el registro nativo y HA no la encuentra. Por eso se
// define cuando <home-assistant> ya existe, leyendo window.customElements en
// ese momento (no antes).
function registerElements() {
  const registry = window.customElements;
  if (!registry.get("meteochile-card")) registry.define("meteochile-card", MeteoChileCard);
  if (!registry.get("meteochile-card-editor")) registry.define("meteochile-card-editor", MeteoChileCardEditor);
}

if (window.customElements.get("home-assistant")) {
  registerElements();
} else {
  window.customElements.whenDefined("home-assistant").then(registerElements);
  // Respaldo para vistas sin <home-assistant> (p. ej. Cast).
  setTimeout(registerElements, 5000);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "meteochile-card")) {
  window.customCards.push({
    type: "meteochile-card",
    name: "MeteoChile",
    description: STRINGS.es.card_description,
    preview: true,
    documentationURL: "https://github.com/matisaul/meteochile-ha",
  });
}

console.info(
  `%c METEOCHILE-CARD %c ${CARD_VERSION} `,
  "color: white; background: #25498f; font-weight: 700;",
  "color: #25498f; background: white; font-weight: 700;"
);
