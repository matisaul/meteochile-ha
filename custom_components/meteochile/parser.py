"""Lectura de los archivos JavaScript que publica la DMC.

La DMC no expone una API: publica archivos .js con variables de JavaScript
(por ejemplo `Pronostico.push({...})`). Este módulo incluye un lector mínimo
de literales JavaScript (objetos, arreglos, strings, números) para extraer
los datos sin ejecutar código.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import re
from typing import Any


class JSParseError(ValueError):
    """Error al leer un literal JavaScript."""


class _LiteralReader:
    """Lector recursivo de literales JavaScript (subconjunto tipo JSON5)."""

    def __init__(self, text: str, pos: int = 0) -> None:
        self.text = text
        self.pos = pos

    def _skip(self) -> None:
        text = self.text
        length = len(text)
        while self.pos < length:
            char = text[self.pos]
            if char.isspace():
                self.pos += 1
            elif text.startswith("//", self.pos):
                end = text.find("\n", self.pos)
                self.pos = length if end == -1 else end + 1
            elif text.startswith("/*", self.pos):
                end = text.find("*/", self.pos + 2)
                if end == -1:
                    raise JSParseError("Comentario sin cerrar")
                self.pos = end + 2
            else:
                break

    def _peek(self) -> str:
        self._skip()
        if self.pos >= len(self.text):
            raise JSParseError("Fin de texto inesperado")
        return self.text[self.pos]

    def read_value(self) -> Any:
        char = self._peek()
        if char == "{":
            return self._read_object()
        if char == "[":
            return self._read_array()
        if char in "\"'":
            return self._read_string()
        return self._read_bare()

    def _read_object(self) -> dict[str, Any]:
        self.pos += 1  # {
        result: dict[str, Any] = {}
        while True:
            char = self._peek()
            if char == "}":
                self.pos += 1
                return result
            if char in "\"'":
                key = self._read_string()
            else:
                match = re.compile(r"[A-Za-z_$][\w$]*").match(self.text, self.pos)
                if not match:
                    raise JSParseError(f"Clave inválida en posición {self.pos}")
                key = match.group(0)
                self.pos = match.end()
            if self._peek() != ":":
                raise JSParseError(f"Se esperaba ':' en posición {self.pos}")
            self.pos += 1
            result[key] = self.read_value()
            char = self._peek()
            if char == ",":
                self.pos += 1
            elif char != "}":
                raise JSParseError(f"Se esperaba ',' o '}}' en posición {self.pos}")

    def _read_array(self) -> list[Any]:
        self.pos += 1  # [
        result: list[Any] = []
        while True:
            char = self._peek()
            if char == "]":
                self.pos += 1
                return result
            result.append(self.read_value())
            char = self._peek()
            if char == ",":
                self.pos += 1
            elif char != "]":
                raise JSParseError(f"Se esperaba ',' o ']' en posición {self.pos}")

    def _read_string(self) -> str:
        quote = self.text[self.pos]
        self.pos += 1
        out: list[str] = []
        escapes = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "0": "\0"}
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == quote:
                self.pos += 1
                return "".join(out)
            if char == "\\":
                nxt = self.text[self.pos + 1 : self.pos + 2]
                if nxt == "u":
                    out.append(chr(int(self.text[self.pos + 2 : self.pos + 6], 16)))
                    self.pos += 6
                    continue
                out.append(escapes.get(nxt, nxt))
                self.pos += 2
                continue
            out.append(char)
            self.pos += 1
        raise JSParseError("String sin cerrar")

    def _read_bare(self) -> Any:
        match = re.compile(r"[^\s,\]\}]+").match(self.text, self.pos)
        if not match:
            raise JSParseError(f"Valor inválido en posición {self.pos}")
        token = match.group(0)
        self.pos = match.end()
        if token == "true":
            return True
        if token == "false":
            return False
        if token in ("null", "undefined"):
            return None
        try:
            return int(token)
        except ValueError:
            pass
        try:
            return float(token)
        except ValueError as err:
            raise JSParseError(f"Valor desconocido: {token}") from err


def read_js_literal(text: str, pos: int = 0) -> tuple[Any, int]:
    """Lee un literal JavaScript desde `pos`. Devuelve (valor, posición final)."""
    reader = _LiteralReader(text, pos)
    value = reader.read_value()
    return value, reader.pos


def decode_bytes(raw: bytes) -> str:
    """Decodifica la respuesta (los archivos de la DMC mezclan UTF-8 y Latin-1)."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def clean_text(value: Any) -> str:
    """Convierte entidades HTML (&aacute;) y <br> a texto plano."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<br\s*/?>", " / ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Pronóstico (pronostico.js)
# --------------------------------------------------------------------------


@dataclass(slots=True)
class DayForecast:
    """Pronóstico de un día para una localidad."""

    label: str
    temp_min: float | None
    temp_max: float | None
    icons: list[str] = field(default_factory=list)  # 4 tramos
    texts: list[str] = field(default_factory=list)  # 4 tramos


@dataclass(slots=True)
class CityForecast:
    """Pronóstico completo de una localidad."""

    key: str
    name: str
    region: str
    base_date: str  # AAAA-MM-DD
    issued: str
    issued_text: str
    days: list[DayForecast]


def _to_float(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _split_temp(value: Any) -> tuple[float | None, float | None]:
    text = str(value or "")
    if "/" not in text:
        return None, _to_float(text)
    low, high = text.split("/", 1)
    return _to_float(low), _to_float(high)


def _period_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_text(item) for item in value]


def parse_forecast(text: str) -> dict[str, CityForecast]:
    """Lee pronostico.js y devuelve {indice_localidad: CityForecast}."""
    cities: dict[str, CityForecast] = {}
    for match in re.finditer(r"Pronostico\s*\.\s*push\s*\(", text):
        try:
            obj, _ = read_js_literal(text, match.end())
        except JSParseError:
            continue
        if not isinstance(obj, dict) or not obj.get("indice"):
            continue

        temps = obj.get("temperatura") or []
        labels = obj.get("fecha") or []
        icons = obj.get("icono") or []
        texts = obj.get("texto") or []

        days: list[DayForecast] = []
        for idx, temp in enumerate(temps):
            low, high = _split_temp(temp)
            days.append(
                DayForecast(
                    label=clean_text(labels[idx]) if idx < len(labels) else "",
                    temp_min=low,
                    temp_max=high,
                    icons=_period_list(icons[idx]) if idx < len(icons) else [],
                    texts=_period_list(texts[idx]) if idx < len(texts) else [],
                )
            )

        key = str(obj["indice"])
        cities[key] = CityForecast(
            key=key,
            name=clean_text(obj.get("ciudad", key)),
            region=str(obj.get("region", "")),
            base_date=str(obj.get("fechasql", "")),
            issued=str(obj.get("fechasqlredaccion", "")),
            issued_text=clean_text(obj.get("redaccion", "")),
            days=days,
        )
    return cities


# --------------------------------------------------------------------------
# Condición actual (condicionactual.js)
# --------------------------------------------------------------------------


@dataclass(slots=True)
class StationObservation:
    """Observación horaria de una estación (aeródromo)."""

    code: str
    time: str
    wind_bearing: float | None
    wind_speed: float | None  # km/h
    visibility: float | None  # km
    present_weather: str
    temperature: float | None
    clouds: str
    icon: str
    humidity: float | None
    description: str


_CURRENT_RE = re.compile(
    r"CondicionActualMetar\s*\[\s*['\"](\w+)['\"]\s*\]\s*=\s*(['\"])(.*?)\2\s*;"
)
_UPDATED_RE = re.compile(r"CondicionActualMetar_actualizado\s*=\s*['\"]([^'\"]*)['\"]")


def parse_current(text: str) -> tuple[dict[str, StationObservation], str | None]:
    """Lee condicionactual.js. Devuelve ({código: observación}, fecha de actualización)."""
    stations: dict[str, StationObservation] = {}
    for match in _CURRENT_RE.finditer(text):
        code = match.group(1)
        parts = match.group(3).split("|")
        parts += [""] * (11 - len(parts))
        visibility_m = _to_float(parts[4])
        bearing = None if parts[2].strip().upper() in ("", "VRB") else _to_float(parts[2])
        stations[code] = StationObservation(
            code=code,
            time=parts[1].strip(),
            wind_bearing=bearing,
            wind_speed=_to_float(parts[3]),
            visibility=(
                None
                if visibility_m is None
                else round(min(visibility_m, 10000) / 1000, 1)
            ),
            present_weather=parts[5].strip(),
            temperature=_to_float(parts[6]),
            clouds=parts[7].strip(),
            icon=parts[8].strip(),
            humidity=_to_float(parts[9]),
            description=clean_text(parts[10]),
        )
    updated = _UPDATED_RE.search(text)
    return stations, (updated.group(1).strip() if updated else None)


# --------------------------------------------------------------------------
# Índice UV (pronostico_radiacion_uv.js)
# --------------------------------------------------------------------------


def parse_uv(text: str) -> dict[str, float]:
    """Lee pronostico_radiacion_uv.js. Devuelve {indice_localidad: índice UV}."""
    match = re.search(r"RadiacionUVB\s*=\s*", text)
    if not match:
        return {}
    try:
        data, _ = read_js_literal(text, match.end())
    except JSParseError:
        return {}
    result: dict[str, float] = {}
    if not isinstance(data, list):
        return result
    for item in data:
        if not isinstance(item, dict) or "codigo" not in item:
            continue
        value = _to_float(str(item.get("indice", "")).replace("+", ""))
        if value is not None:
            result[str(item["codigo"])] = value
    return result
