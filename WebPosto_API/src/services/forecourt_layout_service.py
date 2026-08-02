"""FORECOURT-CONFIG — ForecourtLayoutService.

Configuração operacional da pista (layout → ilha → posição → bico ERP).
Isolamento multi-tenant por station_id (= empresa_codigo). Sem hardcode de filial.
Persistência: JSON auditável em data/forecourt_layouts.json (padrão fraud_settings).
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.core.config import OFFICIAL_COMPANY_CODES
from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_JSON_PATH = _DATA_DIR / "forecourt_layouts.json"
_SEED_CASA_PATH = _DATA_DIR / "forecourt_seed_casa_caiada.json"
_SEED_REAL_PATH = _DATA_DIR / "forecourt_seed_posto_real.json"

LAYOUT_STATUSES = frozenset({"DRAFT", "ACTIVE", "ARCHIVED"})
MAPPING_STATUSES = frozenset({"PROVISIONAL", "CONFIRMED"})
ORIENTATIONS = frozenset(
    {
        "AVENIDA",
        "CONVENIENCIA",
        "LATERAL",
        "FUNDOS",
        "INTERNA",
        "OUTRA",
        # Sensores líquidos — orientação física não confirmada (sem inventar AVENIDA/CONV)
        "UNCONFIRMED",
        "SENSOR",
        "GNV",
    }
)


class ForecourtValidationError(ValueError):
    """Erro de regra de negócio do layout."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


# ── DTOs ─────────────────────────────────────────────────────────────────────


class NozzleLinkDTO(BaseModel):
    nozzle_id: int = Field(..., ge=1, description="Código bico ERP")
    active: bool = True
    label: str = ""


class PositionDTO(BaseModel):
    id: str | None = None
    island_code: str
    pump_id: int = Field(..., ge=1)
    pump_name: str = ""
    code: str
    name: str = ""
    orientation: str = "AVENIDA"
    x: float = 0.0
    y: float = 0.0
    active: bool = True
    operational: bool = True
    nozzles: list[NozzleLinkDTO] = Field(default_factory=list)


class ZoneDTO(BaseModel):
    code: str
    name: str = ""
    display_order: int = 0
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None


class MarkerDTO(BaseModel):
    """Marcador orientativo no canvas (ex.: BR-101) — dados do seed, sem hardcode no FE."""

    code: str
    label: str = ""
    x: float = 0.0
    y: float = 0.0


class IslandDTO(BaseModel):
    id: str | None = None
    code: str
    name: str = ""
    zone_code: str = ""
    display_order: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 120.0
    height: float = 80.0
    active: bool = True


class LayoutCreateDTO(BaseModel):
    station_id: int
    name: str = "Layout"
    mapping_status: str = "PROVISIONAL"
    mapping_note: str = ""
    coordinate_width: int = 1000
    coordinate_height: int = 600
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    zones: list[ZoneDTO] = Field(default_factory=list)
    markers: list[MarkerDTO] = Field(default_factory=list)
    islands: list[IslandDTO] = Field(default_factory=list)
    positions: list[PositionDTO] = Field(default_factory=list)


class LayoutUpdateDTO(BaseModel):
    name: str | None = None
    mapping_status: str | None = None
    mapping_note: str | None = None
    coordinate_width: int | None = None
    coordinate_height: int | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    zones: list[ZoneDTO] | None = None
    markers: list[MarkerDTO] | None = None
    islands: list[IslandDTO] | None = None
    positions: list[PositionDTO] | None = None


class NozzleResolutionDTO(BaseModel):
    """Cadeia BICO → POSIÇÃO/SENSOR → ORIENTAÇÃO → BOMBA → ILHA → ZONA → COORDENADAS."""

    station_id: int
    nozzle_id: int
    layout_id: str
    layout_version: int
    position_id: str
    position_code: str
    orientation: str
    pump_id: int
    pump_name: str = ""
    island_id: str
    island_code: str
    zone_code: str = ""
    zone_name: str = ""
    coordinates: dict[str, float]
    island_coordinates: dict[str, float]


# ── Pure validators (testáveis sem I/O) ───────────────────────────────────────


def assert_known_station(station_id: int | str) -> int:
    """Resolve e valida posto oficial — sem hardcode de filial específica."""
    resolved = resolve_empresa_codigo(station_id)
    if resolved is None:
        raise ForecourtValidationError(
            "UNKNOWN_STATION",
            f"station_id={station_id} não resolve para posto oficial",
        )
    if int(resolved) not in OFFICIAL_COMPANY_CODES:
        raise ForecourtValidationError(
            "STATION_NOT_LICENSED",
            f"station_id={resolved} fora do escopo de postos licenciados",
        )
    return int(resolved)


def validate_forecourt_layout_payload(
    *,
    station_id: int,
    islands: list[IslandDTO],
    positions: list[PositionDTO],
    status: str = "DRAFT",
    mapping_status: str = "PROVISIONAL",
    other_active_overlapping: bool = False,
) -> list[str]:
    """Validações determinísticas. Retorna warnings; levanta em erros fatais."""
    warnings: list[str] = []
    assert_known_station(station_id)

    if status not in LAYOUT_STATUSES:
        raise ForecourtValidationError("INVALID_STATUS", f"status inválido: {status}")
    if mapping_status not in MAPPING_STATUSES:
        raise ForecourtValidationError(
            "INVALID_MAPPING_STATUS", f"mapping_status inválido: {mapping_status}"
        )

    if status == "ACTIVE" and other_active_overlapping:
        raise ForecourtValidationError(
            "ACTIVE_LAYOUT_CONFLICT",
            "Já existe layout ACTIVE sobreposto no período para este posto",
        )

    island_codes = [i.code.strip() for i in islands]
    if len(island_codes) != len(set(island_codes)):
        raise ForecourtValidationError(
            "DUPLICATE_ISLAND_CODE", "Códigos de ilha duplicados no layout"
        )
    island_set = set(island_codes)

    pos_codes: list[str] = []
    nozzles_seen: dict[int, str] = {}
    pumps_ok: set[int] = set()

    for p in positions:
        code = p.code.strip()
        if code in pos_codes:
            raise ForecourtValidationError(
                "DUPLICATE_POSITION_CODE", f"Posição duplicada: {code}"
            )
        pos_codes.append(code)
        if p.island_code.strip() not in island_set:
            raise ForecourtValidationError(
                "ISLAND_NOT_FOUND",
                f"Posição {code} referencia ilha inexistente: {p.island_code}",
            )
        if p.orientation.upper() not in ORIENTATIONS:
            raise ForecourtValidationError(
                "INVALID_ORIENTATION",
                f"Orientação inválida: {p.orientation}",
            )
        if p.pump_id < 1:
            raise ForecourtValidationError("INVALID_PUMP", "pump_id deve ser >= 1")
        pumps_ok.add(int(p.pump_id))

        for n in p.nozzles:
            nid = int(n.nozzle_id)
            if nid < 1:
                raise ForecourtValidationError("INVALID_NOZZLE", "nozzle_id deve ser >= 1")
            if nid in nozzles_seen:
                raise ForecourtValidationError(
                    "DUPLICATE_NOZZLE",
                    f"Bico ERP {nid} já vinculado à posição {nozzles_seen[nid]} "
                    f"(não pode duplicar no mesmo layout)",
                )
            nozzles_seen[nid] = code

    if status == "ACTIVE" and not nozzles_seen:
        warnings.append("ACTIVE_WITHOUT_NOZZLES")

    return warnings


def periods_overlap(
    a_from: datetime | None,
    a_to: datetime | None,
    b_from: datetime | None,
    b_to: datetime | None,
) -> bool:
    """True se intervalos [from, to) se sobrepõem (None = aberto)."""
    a0 = a_from or datetime.min.replace(tzinfo=timezone.utc)
    a1 = a_to or datetime.max.replace(tzinfo=timezone.utc)
    b0 = b_from or datetime.min.replace(tzinfo=timezone.utc)
    b1 = b_to or datetime.max.replace(tzinfo=timezone.utc)
    if a0.tzinfo is None:
        a0 = a0.replace(tzinfo=timezone.utc)
    if a1.tzinfo is None:
        a1 = a1.replace(tzinfo=timezone.utc)
    if b0.tzinfo is None:
        b0 = b0.replace(tzinfo=timezone.utc)
    if b1.tzinfo is None:
        b1 = b1.replace(tzinfo=timezone.utc)
    return a0 < b1 and b0 < a1


# ── In-memory store (testes + fallback) ──────────────────────────────────────


class _MemStore:
    def __init__(self) -> None:
        self.layouts: dict[str, dict[str, Any]] = {}


_MEM = _MemStore()


def _island_dto(raw: dict[str, Any]) -> IslandDTO:
    return IslandDTO(
        id=raw.get("id"),
        code=str(raw["code"]),
        name=str(raw.get("name") or ""),
        zone_code=str(raw.get("zone_code") or ""),
        display_order=int(raw.get("display_order") or 0),
        x=float(raw.get("x") or 0),
        y=float(raw.get("y") or 0),
        width=float(raw.get("width") or 120),
        height=float(raw.get("height") or 80),
        active=bool(raw.get("active", True)),
    )


def _position_dto(raw: dict[str, Any]) -> PositionDTO:
    return PositionDTO(
        id=raw.get("id"),
        island_code=str(raw["island_code"]),
        pump_id=int(raw["pump_id"]),
        pump_name=str(raw.get("pump_name") or ""),
        code=str(raw["code"]),
        name=str(raw.get("name") or ""),
        orientation=str(raw.get("orientation") or "AVENIDA"),
        x=float(raw.get("x") or 0),
        y=float(raw.get("y") or 0),
        active=bool(raw.get("active", True)),
        operational=bool(raw.get("operational", True)),
        nozzles=[
            NozzleLinkDTO(
                nozzle_id=int(n["nozzle_id"]),
                active=bool(n.get("active", True)),
                label=str(n.get("label") or ""),
            )
            for n in raw.get("nozzles") or []
        ],
    )


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _serialize_layout(record: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(record)
    for key in ("valid_from", "valid_to"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    return out


def _deserialize_layout(raw: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(raw)
    out["valid_from"] = _parse_dt(out.get("valid_from"))
    out["valid_to"] = _parse_dt(out.get("valid_to"))
    return out


class ForecourtLayoutService:
    """Service Layer — CRUD + validação + resolução de cadeia + JSON persist."""

    def __init__(self, *, use_memory: bool = True, isolated: bool = False) -> None:
        self.use_memory = use_memory
        self._persist_enabled = not isolated
        self._store = _MemStore() if isolated else _MEM
        if self._persist_enabled and not self._store.layouts:
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not _JSON_PATH.exists():
            return
        try:
            payload = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
            rows = payload.get("layouts") if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                return
            for row in rows:
                if not isinstance(row, dict) or not row.get("id"):
                    continue
                self._store.layouts[str(row["id"])] = _deserialize_layout(row)
            LOGGER.info(
                "forecourt_layout loaded from disk count=%s path=%s",
                len(self._store.layouts),
                _JSON_PATH,
            )
        except Exception as exc:
            LOGGER.warning("forecourt_layout load failed: %s", exc)

    def _save_to_disk(self) -> None:
        if not self._persist_enabled:
            return
        try:
            _JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
            rows = [_serialize_layout(L) for L in self._store.layouts.values()]
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "layouts": rows,
            }
            _JSON_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as exc:
            LOGGER.warning("forecourt_layout persist failed: %s", exc)

    def _next_version(self, station_id: int) -> int:
        vers = [
            int(L["version"])
            for L in self._store.layouts.values()
            if int(L["station_id"]) == station_id
        ]
        return (max(vers) + 1) if vers else 1

    def _has_active_overlap(
        self,
        station_id: int,
        valid_from: datetime | None,
        valid_to: datetime | None,
        exclude_id: str | None = None,
    ) -> bool:
        for lid, L in self._store.layouts.items():
            if exclude_id and lid == exclude_id:
                continue
            if int(L["station_id"]) != station_id:
                continue
            if L["status"] != "ACTIVE":
                continue
            if periods_overlap(valid_from, valid_to, L.get("valid_from"), L.get("valid_to")):
                return True
        return False

    def validate_forecourt_layout(self, layout_id: str) -> dict[str, Any]:
        L = self._store.layouts.get(layout_id)
        if not L:
            raise ForecourtValidationError("LAYOUT_NOT_FOUND", f"layout {layout_id}")
        # Tenant check implícito via station_id do próprio layout
        warnings = validate_forecourt_layout_payload(
            station_id=int(L["station_id"]),
            islands=[_island_dto(i) for i in L["islands"]],
            positions=[_position_dto(p) for p in L["positions"]],
            status=L["status"],
            mapping_status=L["mapping_status"],
            other_active_overlapping=False,
        )
        return {"ok": True, "layout_id": layout_id, "warnings": warnings}

    def create_layout(self, body: LayoutCreateDTO) -> dict[str, Any]:
        station_id = assert_known_station(body.station_id)
        validate_forecourt_layout_payload(
            station_id=station_id,
            islands=body.islands,
            positions=body.positions,
            status="DRAFT",
            mapping_status=body.mapping_status.upper(),
        )
        layout_id = f"FL-{station_id}-{uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        # Assign stable ids
        islands = []
        for i in body.islands:
            islands.append(
                {
                    **i.model_dump(),
                    "id": i.id or f"ISL-{uuid4().hex[:8]}",
                    "code": i.code.strip(),
                }
            )
        code_to_id = {i["code"]: i["id"] for i in islands}
        positions = []
        for p in body.positions:
            positions.append(
                {
                    **p.model_dump(),
                    "id": p.id or f"POS-{uuid4().hex[:8]}",
                    "island_code": p.island_code.strip(),
                    "island_id": code_to_id.get(p.island_code.strip()),
                    "orientation": p.orientation.upper(),
                    "code": p.code.strip(),
                    "nozzles": [n.model_dump() for n in p.nozzles],
                }
            )
        zones = [
            {**z.model_dump(), "code": z.code.strip(), "name": z.name or z.code}
            for z in body.zones
        ]
        markers = [
            {
                **m.model_dump(),
                "code": m.code.strip(),
                "label": m.label or m.code,
            }
            for m in body.markers
        ]
        record = {
            "id": layout_id,
            "station_id": station_id,
            "version": self._next_version(station_id),
            "name": body.name,
            "status": "DRAFT",
            "mapping_status": body.mapping_status.upper(),
            "mapping_note": body.mapping_note or "",
            "valid_from": body.valid_from,
            "valid_to": body.valid_to,
            "coordinate_width": body.coordinate_width,
            "coordinate_height": body.coordinate_height,
            "zones": zones,
            "markers": markers,
            "islands": islands,
            "positions": positions,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        self._store.layouts[layout_id] = record
        self._save_to_disk()
        LOGGER.info(
            "forecourt_layout.create id=%s station=%s version=%s",
            layout_id,
            station_id,
            record["version"],
        )
        return deepcopy(record)

    def update_layout(self, layout_id: str, body: LayoutUpdateDTO) -> dict[str, Any]:
        L = self._store.layouts.get(layout_id)
        if not L:
            raise ForecourtValidationError("LAYOUT_NOT_FOUND", f"layout {layout_id}")
        if L["status"] == "ARCHIVED":
            raise ForecourtValidationError("LAYOUT_ARCHIVED", "Layout arquivado é imutável")

        if body.name is not None:
            L["name"] = body.name
        if body.mapping_status is not None:
            L["mapping_status"] = body.mapping_status.upper()
        if body.mapping_note is not None:
            L["mapping_note"] = body.mapping_note
        if body.markers is not None:
            L["markers"] = [
                {**m.model_dump(), "code": m.code.strip(), "label": m.label or m.code}
                for m in body.markers
            ]
        if body.coordinate_width is not None:
            L["coordinate_width"] = body.coordinate_width
        if body.coordinate_height is not None:
            L["coordinate_height"] = body.coordinate_height
        if body.valid_from is not None:
            L["valid_from"] = body.valid_from
        if body.valid_to is not None:
            L["valid_to"] = body.valid_to

        if body.zones is not None:
            L["zones"] = [
                {**z.model_dump(), "code": z.code.strip(), "name": z.name or z.code}
                for z in body.zones
            ]
        if body.islands is not None:
            L["islands"] = [
                {**i.model_dump(), "id": i.id or f"ISL-{uuid4().hex[:8]}", "code": i.code.strip()}
                for i in body.islands
            ]
        if body.positions is not None:
            code_to_id = {i["code"]: i["id"] for i in L["islands"]}
            L["positions"] = [
                {
                    **p.model_dump(),
                    "id": p.id or f"POS-{uuid4().hex[:8]}",
                    "island_code": p.island_code.strip(),
                    "island_id": code_to_id.get(p.island_code.strip()),
                    "orientation": p.orientation.upper(),
                    "code": p.code.strip(),
                    "nozzles": [n.model_dump() for n in p.nozzles],
                }
                for p in body.positions
            ]

        validate_forecourt_layout_payload(
            station_id=int(L["station_id"]),
            islands=[_island_dto(i) for i in L["islands"]],
            positions=[_position_dto(p) for p in L["positions"]],
            status=L["status"],
            mapping_status=L["mapping_status"],
        )
        L["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_to_disk()
        return deepcopy(L)

    def activate_layout(self, layout_id: str, *, requester_station_id: int | None = None) -> dict[str, Any]:
        L = self._store.layouts.get(layout_id)
        if not L:
            raise ForecourtValidationError("LAYOUT_NOT_FOUND", f"layout {layout_id}")

        station_id = int(L["station_id"])
        if requester_station_id is not None:
            req = assert_known_station(requester_station_id)
            if req != station_id:
                raise ForecourtValidationError(
                    "TENANT_FORBIDDEN",
                    f"Posto {req} não pode ativar layout do posto {station_id}",
                )

        overlap = self._has_active_overlap(
            station_id, L.get("valid_from"), L.get("valid_to"), exclude_id=layout_id
        )
        validate_forecourt_layout_payload(
            station_id=station_id,
            islands=[_island_dto(i) for i in L["islands"]],
            positions=[_position_dto(p) for p in L["positions"]],
            status="ACTIVE",
            mapping_status=L["mapping_status"],
            other_active_overlapping=overlap,
        )
        L["status"] = "ACTIVE"
        L["updated_at"] = datetime.now(timezone.utc).isoformat()
        if L.get("valid_from") is None:
            L["valid_from"] = datetime.now(timezone.utc)
        self._save_to_disk()
        return deepcopy(L)

    def archive_layout(self, layout_id: str) -> dict[str, Any]:
        L = self._store.layouts.get(layout_id)
        if not L:
            raise ForecourtValidationError("LAYOUT_NOT_FOUND", f"layout {layout_id}")
        L["status"] = "ARCHIVED"
        L["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_to_disk()
        return deepcopy(L)

    def list_layouts(self, station_id: int | None = None) -> list[dict[str, Any]]:
        rows = list(self._store.layouts.values())
        if station_id is not None:
            sid = assert_known_station(station_id)
            rows = [r for r in rows if int(r["station_id"]) == sid]
        rows.sort(key=lambda r: (-int(r["version"]), r["id"]))
        return [deepcopy(r) for r in rows]

    def get_layout(self, layout_id: str, *, requester_station_id: int | None = None) -> dict[str, Any]:
        L = self._store.layouts.get(layout_id)
        if not L:
            raise ForecourtValidationError("LAYOUT_NOT_FOUND", f"layout {layout_id}")
        if requester_station_id is not None:
            req = assert_known_station(requester_station_id)
            if req != int(L["station_id"]):
                raise ForecourtValidationError(
                    "TENANT_FORBIDDEN",
                    f"Acesso negado: layout pertence ao posto {L['station_id']}",
                )
        return deepcopy(L)

    def get_active_layout(self, station_id: int) -> dict[str, Any] | None:
        sid = assert_known_station(station_id)
        now = datetime.now(timezone.utc)
        candidates = [
            L
            for L in self._store.layouts.values()
            if int(L["station_id"]) == sid and L["status"] == "ACTIVE"
        ]
        for L in sorted(candidates, key=lambda x: -int(x["version"])):
            vf, vt = L.get("valid_from"), L.get("valid_to")
            if periods_overlap(now, now, vf, vt) or (vf is None and vt is None):
                return deepcopy(L)
        return deepcopy(candidates[0]) if candidates else None

    def resolve_nozzle(
        self,
        station_id: int,
        nozzle_id: int,
        *,
        layout_id: str | None = None,
    ) -> NozzleResolutionDTO:
        """BICO → POSIÇÃO → ORIENTAÇÃO → BOMBA → ILHA → COORDENADAS."""
        sid = assert_known_station(station_id)
        if layout_id:
            L = self.get_layout(layout_id, requester_station_id=sid)
        else:
            L = self.get_active_layout(sid)
            if not L:
                raise ForecourtValidationError(
                    "NO_ACTIVE_LAYOUT",
                    f"Nenhum layout ACTIVE para station_id={sid}",
                )

        if int(L["station_id"]) != sid:
            raise ForecourtValidationError("TENANT_FORBIDDEN", "Layout de outro posto")

        island_by_code = {i["code"]: i for i in L["islands"]}
        zone_by_code = {
            str(z.get("code")): z for z in (L.get("zones") or []) if z.get("code")
        }
        for p in L["positions"]:
            for n in p.get("nozzles") or []:
                if int(n["nozzle_id"]) != int(nozzle_id):
                    continue
                if not n.get("active", True):
                    continue
                island = island_by_code.get(p["island_code"]) or {}
                zone_code = str(island.get("zone_code") or "")
                zone = zone_by_code.get(zone_code) or {}
                return NozzleResolutionDTO(
                    station_id=sid,
                    nozzle_id=int(nozzle_id),
                    layout_id=L["id"],
                    layout_version=int(L["version"]),
                    position_id=str(p["id"]),
                    position_code=p["code"],
                    orientation=str(p.get("orientation") or "AVENIDA"),
                    pump_id=int(p["pump_id"]),
                    pump_name=str(p.get("pump_name") or ""),
                    island_id=str(island.get("id") or p.get("island_id") or ""),
                    island_code=str(p["island_code"]),
                    zone_code=zone_code,
                    zone_name=str(zone.get("name") or zone_code),
                    coordinates={"x": float(p.get("x") or 0), "y": float(p.get("y") or 0)},
                    island_coordinates={
                        "x": float(island.get("x") or 0),
                        "y": float(island.get("y") or 0),
                        "width": float(island.get("width") or 0),
                        "height": float(island.get("height") or 0),
                    },
                )
        raise ForecourtValidationError(
            "NOZZLE_NOT_MAPPED",
            f"Bico {nozzle_id} não mapeado no layout {L['id']}",
        )

    def layout_summary(self, layout: dict[str, Any]) -> dict[str, Any]:
        positions = layout.get("positions") or []
        islands = layout.get("islands") or []
        zones = layout.get("zones") or []
        pumps = {int(p.get("pump_id") or 0) for p in positions if p.get("pump_id")}
        nozzles = set()
        for p in positions:
            for n in p.get("nozzles") or []:
                nozzles.add(int(n["nozzle_id"]))
        liq_islands = [i for i in islands if str(i.get("zone_code") or "") == "ZONE_LIQUIDOS"]
        gnv_islands = [i for i in islands if str(i.get("zone_code") or "") == "ZONE_GNV"]
        liq_pumps = {
            int(p.get("pump_id") or 0)
            for p in positions
            if any(
                i.get("code") == p.get("island_code") and i.get("zone_code") == "ZONE_LIQUIDOS"
                for i in islands
            )
        }
        liq_positions = [
            p
            for p in positions
            if any(
                i.get("code") == p.get("island_code") and i.get("zone_code") == "ZONE_LIQUIDOS"
                for i in islands
            )
        ]
        return {
            "layout_id": layout.get("id"),
            "name": layout.get("name"),
            "station_id": layout.get("station_id"),
            "version": layout.get("version"),
            "status": layout.get("status"),
            "mapping_status": layout.get("mapping_status"),
            "mapping_note": layout.get("mapping_note") or "",
            "qtd_zonas": len(zones),
            "qtd_ilhas": len(islands),
            "qtd_ilhas_liquidos": len(liq_islands),
            "qtd_equip_gnv": len(gnv_islands),
            "qtd_bombas": len(pumps),
            "qtd_bombas_liquidos": len({p for p in liq_pumps if p}),
            "qtd_posicoes": len(positions),
            "qtd_posicoes_liquidos": len(liq_positions),
            "qtd_bicos": len(nozzles),
        }

    def seed_from_file(self, seed_path: Path, *, force: bool = False) -> dict[str, Any]:
        """Seed idempotente genérico a partir de JSON auditável (alias → station_id)."""
        if not seed_path.exists():
            raise ForecourtValidationError(
                "SEED_FILE_MISSING", f"Arquivo de seed ausente: {seed_path.name}"
            )
        seed = json.loads(seed_path.read_text(encoding="utf-8"))
        alias = seed.get("station_alias")
        if not alias:
            raise ForecourtValidationError("SEED_INVALID", "station_alias obrigatório no seed")
        station_id = assert_known_station(alias)
        layout_spec = seed.get("layout") or {}
        name = str(layout_spec.get("name") or "Layout")

        existing = [
            L
            for L in self._store.layouts.values()
            if int(L["station_id"]) == station_id
            and L.get("name") == name
            and L.get("status") != "ARCHIVED"
        ]
        if existing and not force:
            L = max(existing, key=lambda x: int(x.get("version") or 0))
            if L.get("status") != "ACTIVE":
                for other in list(self._store.layouts.values()):
                    if (
                        int(other["station_id"]) == station_id
                        and other["status"] == "ACTIVE"
                        and other["id"] != L["id"]
                    ):
                        other["status"] = "ARCHIVED"
                activated = self.activate_layout(L["id"])
                activated["seed_id"] = seed.get("seed_id")
                activated["seeded"] = False
                activated["summary"] = self.layout_summary(activated)
                return activated
            return {
                **deepcopy(L),
                "seed_id": seed.get("seed_id"),
                "seeded": False,
                "summary": self.layout_summary(L),
            }

        if force:
            for L in list(self._store.layouts.values()):
                if int(L["station_id"]) == station_id and L["status"] == "ACTIVE":
                    L["status"] = "ARCHIVED"

        body = LayoutCreateDTO(
            station_id=station_id,
            name=name,
            mapping_status=str(layout_spec.get("mapping_status") or "PROVISIONAL"),
            mapping_note=str(layout_spec.get("mapping_note") or ""),
            coordinate_width=int(layout_spec.get("coordinate_width") or 1000),
            coordinate_height=int(layout_spec.get("coordinate_height") or 600),
            zones=[ZoneDTO(**z) for z in layout_spec.get("zones") or []],
            markers=[MarkerDTO(**m) for m in layout_spec.get("markers") or []],
            islands=[IslandDTO(**i) for i in layout_spec.get("islands") or []],
            positions=[PositionDTO(**p) for p in layout_spec.get("positions") or []],
        )
        created = self.create_layout(body)
        for other in list(self._store.layouts.values()):
            if (
                int(other["station_id"]) == station_id
                and other["status"] == "ACTIVE"
                and other["id"] != created["id"]
            ):
                other["status"] = "ARCHIVED"
                other["updated_at"] = datetime.now(timezone.utc).isoformat()
        activated = self.activate_layout(created["id"])
        activated["seed_id"] = seed.get("seed_id")
        activated["seeded"] = True
        activated["summary"] = self.layout_summary(activated)
        LOGGER.info(
            "forecourt_layout.seed station=%s id=%s seed_id=%s file=%s",
            station_id,
            activated["id"],
            seed.get("seed_id"),
            seed_path.name,
        )
        return activated

    def seed_casa_caiada_pilot(self, *, force: bool = False) -> dict[str, Any]:
        """Seed auditável Casa Caiada — data/forecourt_seed_casa_caiada.json."""
        return self.seed_from_file(_SEED_CASA_PATH, force=force)

    def seed_posto_real_pilot(self, *, force: bool = False) -> dict[str, Any]:
        """Seed auditável Posto Doze/Real — data/forecourt_seed_posto_real.json."""
        return self.seed_from_file(_SEED_REAL_PATH, force=force)

    def reset_memory(self) -> None:
        """Apenas testes."""
        self._store.layouts.clear()


_svc: ForecourtLayoutService | None = None


def get_forecourt_layout_service() -> ForecourtLayoutService:
    global _svc
    if _svc is None:
        _svc = ForecourtLayoutService(use_memory=True, isolated=False)
    return _svc
