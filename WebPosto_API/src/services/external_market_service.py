"""Integração com indicadores reais de mercado (USD, Brent, Esalq/CEPEA).

Fontes:
- USD/BRL: AwesomeAPI (com chave opcional) → BCB PTAX → Frankfurter
- Brent: Yahoo Finance (BZ=F) → fallback contingência
- Etanol Esalq PE/AL: parser CEPEA → fallback contingência

Falhas externas nunca derrubam o painel: log + fallback + flag `fonte`.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import httpx

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

# Contingência (último recurso) — valores tipicamente observados no NE.
_FALLBACK_USD_BRL = 5.50
_FALLBACK_BRENT_USD = 80.0
_FALLBACK_ESALQ_PE = 2.80
_FALLBACK_ESALQ_AL = 2.75

# Coordenadas reais aproximadas das filiais Grupo Lisboa (Olinda/Recife - PE).
BRANCH_GEOCOORDINATES: dict[int, dict[str, Any]] = {
    5555: {
        "empresa_nome": "AP Casa Caiada",
        "bairro": "Casa Caiada",
        "cidade": "Olinda",
        "uf": "PE",
        "latitude": -7.9908,
        "longitude": -34.8395,
    },
    6666: {
        "empresa_nome": "Posto VIP / Rio Doce",
        "bairro": "Rio Doce",
        "cidade": "Olinda",
        "uf": "PE",
        "latitude": -7.9685,
        "longitude": -34.8502,
    },
    11495: {
        "empresa_nome": "Posto VIP Rede",
        "bairro": "Rio Doce",
        "cidade": "Olinda",
        "uf": "PE",
        "latitude": -7.9685,
        "longitude": -34.8502,
    },
    74014: {
        "empresa_nome": "Posto Real / Doze Filial II",
        "bairro": "Imbiribeira",
        "cidade": "Recife",
        "uf": "PE",
        "latitude": -8.1124,
        "longitude": -34.9138,
    },
}


@dataclass
class MarketQuote:
    """Cotação individual com metadados de origem."""

    value: float
    source: str
    is_fallback: bool = False
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_label: str = ""


@dataclass
class LiveMarketIndicators:
    """Pacote consolidado de indicadores para o cockpit."""

    usd_brl: MarketQuote
    brent_usd: MarketQuote
    esalq_etanol_pe: MarketQuote
    esalq_etanol_al: MarketQuote
    branches_geo: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "usd_brl": self.usd_brl.value,
            "brent_usd": self.brent_usd.value,
            "esalq_etanol_pe": self.esalq_etanol_pe.value,
            "esalq_etanol_al": self.esalq_etanol_al.value,
            "sources": {
                "usd_brl": self.usd_brl.source,
                "brent_usd": self.brent_usd.source,
                "esalq_etanol_pe": self.esalq_etanol_pe.source,
                "esalq_etanol_al": self.esalq_etanol_al.source,
            },
            "is_fallback": {
                "usd_brl": self.usd_brl.is_fallback,
                "brent_usd": self.brent_usd.is_fallback,
                "esalq_etanol_pe": self.esalq_etanol_pe.is_fallback,
                "esalq_etanol_al": self.esalq_etanol_al.is_fallback,
            },
            "branches_geo": self.branches_geo,
            "warnings": self.warnings,
            "data_atualizacao": self.fetched_at.isoformat(),
        }


class ExternalMarketService:
    """Cliente HTTP para cotações públicas de mercado."""

    def __init__(self, timeout_seconds: float | None = None) -> None:
        self._timeout = timeout_seconds or float(
            getattr(settings, "market_data_timeout_seconds", 12.0) or 12.0
        )
        self._api_key = (
            getattr(settings, "market_data_api_key", "") or ""
        ).strip()
        self._cache: LiveMarketIndicators | None = None
        self._cache_ttl_seconds = int(
            getattr(settings, "market_data_cache_ttl_seconds", 300) or 300
        )

    def _client(self) -> httpx.AsyncClient:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.cepea.esalq.usp.br/",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return httpx.AsyncClient(timeout=self._timeout, headers=headers, follow_redirects=True)

    async def fetch_usd_brl(self) -> MarketQuote:
        """Busca USD/BRL com cascata de fontes."""
        async with self._client() as client:
            # 1) AwesomeAPI (opcionalmente com chave)
            try:
                url = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
                if self._api_key:
                    url = f"{url}?token={self._api_key}"
                resp = await client.get(url)
                if resp.status_code == 200:
                    payload = resp.json()
                    node = payload.get("USDBRL") or payload.get("USD-BRL") or {}
                    bid = float(node.get("bid") or node.get("ask") or 0)
                    if bid > 0:
                        return MarketQuote(
                            value=round(bid, 4),
                            source="awesomeapi",
                            raw_label=str(node.get("create_date") or ""),
                        )
                logger.warning(
                    "AwesomeAPI USD falhou: status=%s body=%s",
                    resp.status_code,
                    (resp.text or "")[:200],
                )
            except Exception as exc:
                logger.warning("AwesomeAPI USD erro: %s", exc)

            # 2) BCB PTAX (público)
            try:
                today = date.today()
                # PTAX usa MM-DD-YYYY; tenta últimos 5 dias úteis
                for offset in range(0, 7):
                    d = date.fromordinal(today.toordinal() - offset)
                    if d.weekday() >= 5:
                        continue
                    cotacao = f"{d.month:02d}-{d.day:02d}-{d.year}"
                    url = (
                        "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
                        f"CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{cotacao}'"
                        "&$top=1&$orderby=dataHoraCotacao%20desc&$format=json"
                    )
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    rows = (resp.json() or {}).get("value") or []
                    if not rows:
                        continue
                    venda = float(rows[0].get("cotacaoVenda") or 0)
                    if venda > 0:
                        return MarketQuote(
                            value=round(venda, 4),
                            source="bcb_ptax",
                            raw_label=str(rows[0].get("dataHoraCotacao") or ""),
                        )
            except Exception as exc:
                logger.warning("BCB PTAX USD erro: %s", exc)

            # 3) Frankfurter
            try:
                resp = await client.get("https://api.frankfurter.app/latest?from=USD&to=BRL")
                if resp.status_code == 200:
                    rate = float((resp.json().get("rates") or {}).get("BRL") or 0)
                    if rate > 0:
                        return MarketQuote(value=round(rate, 4), source="frankfurter")
            except Exception as exc:
                logger.warning("Frankfurter USD erro: %s", exc)

        logger.error("USD/BRL: todas as fontes falharam — usando fallback %.2f", _FALLBACK_USD_BRL)
        return MarketQuote(value=_FALLBACK_USD_BRL, source="fallback_contingencia", is_fallback=True)

    async def fetch_brent_usd(self) -> MarketQuote:
        """Busca Brent (USD/bbl) via Yahoo Finance chart API."""
        async with self._client() as client:
            try:
                url = "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?interval=1d&range=5d"
                resp = await client.get(url)
                if resp.status_code == 200:
                    chart = ((resp.json() or {}).get("chart") or {}).get("result") or []
                    if chart:
                        meta = chart[0].get("meta") or {}
                        price = float(
                            meta.get("regularMarketPrice")
                            or meta.get("previousClose")
                            or 0
                        )
                        if price > 0:
                            return MarketQuote(
                                value=round(price, 2),
                                source="yahoo_finance_BZ=F",
                                raw_label=str(meta.get("symbol") or "BZ=F"),
                            )
                logger.warning(
                    "Yahoo Brent falhou: status=%s body=%s",
                    resp.status_code,
                    (resp.text or "")[:200],
                )
            except Exception as exc:
                logger.warning("Yahoo Brent erro: %s", exc)

            # AwesomeAPI petroleum (quando disponível)
            try:
                url = "https://economia.awesomeapi.com.br/json/last/PETROLEUM-USD"
                if self._api_key:
                    url = f"{url}?token={self._api_key}"
                resp = await client.get(url)
                if resp.status_code == 200:
                    payload = resp.json()
                    node = next(iter(payload.values()), {}) if isinstance(payload, dict) else {}
                    bid = float(node.get("bid") or 0)
                    if bid > 0:
                        return MarketQuote(value=round(bid, 2), source="awesomeapi_petroleum")
            except Exception as exc:
                logger.warning("AwesomeAPI petroleum erro: %s", exc)

        logger.error("Brent: todas as fontes falharam — usando fallback %.2f", _FALLBACK_BRENT_USD)
        return MarketQuote(value=_FALLBACK_BRENT_USD, source="fallback_contingencia", is_fallback=True)

    async def fetch_esalq_etanol(self) -> tuple[MarketQuote, MarketQuote]:
        """Lê preço médio do etanol hidratado CEPEA (PE/AL) com parser HTML."""
        pe = MarketQuote(value=_FALLBACK_ESALQ_PE, source="fallback_contingencia", is_fallback=True)
        al = MarketQuote(value=_FALLBACK_ESALQ_AL, source="fallback_contingencia", is_fallback=True)

        urls = (
            "https://www.cepea.esalq.usp.br/br/indicador/etanol.aspx",
            "https://www.cepea.esalq.usp.br/br/indicador/series/etanol.aspx?id=103",
            "https://www.cepea.esalq.usp.br/br/indicador/series/etanol.aspx?id=104",
        )

        async with self._client() as client:
            for url in urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning("CEPEA etanol status=%s url=%s", resp.status_code, url)
                        continue

                    candidates = self._parse_cepea_etanol_prices(resp.text or "")
                    if candidates.get("pe"):
                        pe = MarketQuote(
                            value=candidates["pe"],
                            source="cepea_esalq_html",
                            is_fallback=False,
                            raw_label=url,
                        )
                    if candidates.get("al"):
                        al = MarketQuote(
                            value=candidates["al"],
                            source="cepea_esalq_html",
                            is_fallback=False,
                            raw_label=url,
                        )
                    elif candidates.get("pe"):
                        al = MarketQuote(
                            value=candidates["pe"],
                            source="cepea_esalq_html_proxy_pe",
                            is_fallback=False,
                            raw_label=url,
                        )

                    if not pe.is_fallback or not al.is_fallback:
                        break
                except Exception as exc:
                    logger.warning("CEPEA etanol erro url=%s: %s", url, exc)

            # Fonte alternativa pública: índice ANP/CEPEA espelhado via dados abertos (quando disponível)
            if pe.is_fallback and al.is_fallback:
                try:
                    alt = await self._fetch_etanol_from_open_proxy(client)
                    if alt:
                        pe, al = alt
                except Exception as exc:
                    logger.warning("Proxy etanol NE erro: %s", exc)

            if pe.is_fallback and al.is_fallback:
                logger.warning(
                    "CEPEA: parser não encontrou preços — fallback PE=%.2f AL=%.2f",
                    _FALLBACK_ESALQ_PE,
                    _FALLBACK_ESALQ_AL,
                )

        return pe, al

    async def _fetch_etanol_from_open_proxy(
        self, client: httpx.AsyncClient
    ) -> tuple[MarketQuote, MarketQuote] | None:
        """
        Contingência secundária: tenta ler cotação de etanol via AwesomeAPI commodities
        ou endpoint público equivalente. Se falhar, retorna None.
        """
        try:
            url = "https://economia.awesomeapi.com.br/json/last/ETHANOL-BRL"
            if self._api_key:
                url = f"{url}?token={self._api_key}"
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            payload = resp.json()
            node = next(iter(payload.values()), {}) if isinstance(payload, dict) else {}
            bid = float(node.get("bid") or 0)
            if bid <= 0:
                return None
            quote = MarketQuote(value=round(bid, 4), source="awesomeapi_ethanol", is_fallback=False)
            return quote, quote
        except Exception:
            return None

    @staticmethod
    def _parse_cepea_etanol_prices(html: str) -> dict[str, float]:
        """Heurística leve para extrair R$/L do etanol hidratado no HTML CEPEA."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        upper = text.upper()
        result: dict[str, float] = {}

        def _nearby_price(label: str) -> float | None:
            idx = upper.find(label)
            if idx < 0:
                return None
            window = text[idx : idx + 180]
            matches = re.findall(r"(\d{1,2},\d{2,4})", window)
            for m in matches:
                try:
                    val = float(m.replace(",", "."))
                    if 1.5 <= val <= 8.0:
                        return round(val, 4)
                except ValueError:
                    continue
            return None

        for key, labels in (
            ("pe", ("PERNAMBUCO", " PE ", "HIDRATADO PE")),
            ("al", ("ALAGOAS", " AL ", "HIDRATADO AL")),
        ):
            for label in labels:
                price = _nearby_price(label)
                if price is not None:
                    result[key] = price
                    break

        # Fallback genérico: primeiro preço plausível após "HIDRATADO"
        if not result:
            idx = upper.find("HIDRATADO")
            if idx >= 0:
                window = text[idx : idx + 250]
                matches = re.findall(r"(\d{1,2},\d{2,4})", window)
                for m in matches:
                    try:
                        val = float(m.replace(",", "."))
                        if 1.5 <= val <= 8.0:
                            result["pe"] = round(val, 4)
                            break
                    except ValueError:
                        continue

        return result

    def get_branch_coordinates(self, empresa_codigo: int | None = None) -> list[dict[str, Any]]:
        """Retorna lat/lng reais das filiais Lisboa."""
        if empresa_codigo is not None:
            geo = BRANCH_GEOCOORDINATES.get(empresa_codigo)
            return [geo] if geo else []
        return list(BRANCH_GEOCOORDINATES.values())

    async def get_live_indicators(self, force_refresh: bool = False) -> LiveMarketIndicators:
        """Consolida todas as cotações com cache curto."""
        if (
            not force_refresh
            and self._cache is not None
            and (datetime.now(timezone.utc) - self._cache.fetched_at).total_seconds()
            < self._cache_ttl_seconds
        ):
            return self._cache

        warnings: list[str] = []
        usd = await self.fetch_usd_brl()
        brent = await self.fetch_brent_usd()
        esalq_pe, esalq_al = await self.fetch_esalq_etanol()

        for quote, name in (
            (usd, "USD/BRL"),
            (brent, "Brent"),
            (esalq_pe, "Esalq PE"),
            (esalq_al, "Esalq AL"),
        ):
            if quote.is_fallback:
                warnings.append(f"{name}: usando contingência ({quote.source})")

        indicators = LiveMarketIndicators(
            usd_brl=usd,
            brent_usd=brent,
            esalq_etanol_pe=esalq_pe,
            esalq_etanol_al=esalq_al,
            branches_geo=self.get_branch_coordinates(),
            warnings=warnings,
        )
        self._cache = indicators
        logger.info(
            "Indicadores de mercado atualizados: USD=%.4f (%s) Brent=%.2f (%s) EsalqPE=%.4f (%s)",
            usd.value,
            usd.source,
            brent.value,
            brent.source,
            esalq_pe.value,
            esalq_pe.source,
        )
        return indicators


_external_market: ExternalMarketService | None = None


def get_external_market_service() -> ExternalMarketService:
    global _external_market
    if _external_market is None:
        _external_market = ExternalMarketService()
    return _external_market
