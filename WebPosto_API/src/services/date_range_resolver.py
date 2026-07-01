"""
Date Range Resolver
Responsável por gerar períodos seguros para consultas WebPosto
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal


DateRangePreset = Literal[
    "today",
    "yesterday", 
    "last_7_days",
    "last_30_days",
    "current_month",
    "previous_month",
    "last_90_days",
]


@dataclass(frozen=True)
class DateRange:
    """Representa um período com data inicial e final"""
    
    start: str  # Formato: YYYY-MM-DD
    end: str    # Formato: YYYY-MM-DD
    
    def __post_init__(self):
        """Valida o formato das datas"""
        if not self.start or not self.end:
            raise ValueError("start and end are required")
        if len(self.start) != 10 or len(self.end) != 10:
            raise ValueError("dates must be in YYYY-MM-DD format")
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) cannot be after end ({self.end})")
    
    def to_params(self) -> dict[str, str]:
        """Retorna os parâmetros prontos para a API WebPosto"""
        return {
            "dataInicial": self.start,
            "dataFinal": self.end,
        }


class DateRangeResolver:
    """Resolvedor de períodos de datas"""
    
    DEFAULT_PRESET: DateRangePreset = "last_7_days"
    
    @staticmethod
    def _format_date(d: date) -> str:
        """Formata uma data para YYYY-MM-DD"""
        return d.isoformat()
    
    @classmethod
    def today(cls) -> DateRange:
        """Período: apenas hoje"""
        today = date.today()
        return DateRange(
            start=cls._format_date(today),
            end=cls._format_date(today),
        )
    
    @classmethod
    def yesterday(cls) -> DateRange:
        """Período: apenas ontem"""
        yesterday = date.today() - timedelta(days=1)
        return DateRange(
            start=cls._format_date(yesterday),
            end=cls._format_date(yesterday),
        )
    
    @classmethod
    def last_7_days(cls) -> DateRange:
        """Período: últimos 7 dias (incluindo hoje)"""
        today = date.today()
        start = today - timedelta(days=6)
        return DateRange(
            start=cls._format_date(start),
            end=cls._format_date(today),
        )
    
    @classmethod
    def last_30_days(cls) -> DateRange:
        """Período: últimos 30 dias (incluindo hoje)"""
        today = date.today()
        start = today - timedelta(days=29)
        return DateRange(
            start=cls._format_date(start),
            end=cls._format_date(today),
        )
    
    @classmethod
    def last_90_days(cls) -> DateRange:
        """Período: últimos 90 dias (incluindo hoje)"""
        today = date.today()
        start = today - timedelta(days=89)
        return DateRange(
            start=cls._format_date(start),
            end=cls._format_date(today),
        )
    
    @classmethod
    def current_month(cls) -> DateRange:
        """Período: mês atual (do dia 1 até hoje)"""
        today = date.today()
        first_day = date(today.year, today.month, 1)
        return DateRange(
            start=cls._format_date(first_day),
            end=cls._format_date(today),
        )
    
    @classmethod
    def previous_month(cls) -> DateRange:
        """Período: mês anterior completo"""
        today = date.today()
        first_day_current = date(today.year, today.month, 1)
        last_day_previous = first_day_current - timedelta(days=1)
        first_day_previous = date(last_day_previous.year, last_day_previous.month, 1)
        return DateRange(
            start=cls._format_date(first_day_previous),
            end=cls._format_date(last_day_previous),
        )
    
    @classmethod
    def custom(cls, start: str, end: str) -> DateRange:
        """Período personalizado"""
        return DateRange(start=start, end=end)
    
    @classmethod
    def resolve(cls, preset: DateRangePreset | None = None) -> DateRange:
        """Resolve um preset para um DateRange"""
        if preset is None:
            preset = cls.DEFAULT_PRESET
        
        if preset == "today":
            return cls.today()
        elif preset == "yesterday":
            return cls.yesterday()
        elif preset == "last_7_days":
            return cls.last_7_days()
        elif preset == "last_30_days":
            return cls.last_30_days()
        elif preset == "last_90_days":
            return cls.last_90_days()
        elif preset == "current_month":
            return cls.current_month()
        elif preset == "previous_month":
            return cls.previous_month()
        else:
            return cls.last_7_days()
    
    @classmethod
    def get_default_range(cls) -> DateRange:
        """Retorna o período padrão (last_7_days)"""
        return cls.resolve(cls.DEFAULT_PRESET)
    
    @classmethod
    def ensure_date_params(
        cls,
        params: dict[str, any] | None,
        *,
        default_preset: DateRangePreset | None = None,
    ) -> dict[str, any]:
        """
        Garante que dataInicial e dataFinal existam nos params.
        Se não existirem, aplica o preset padrão.
        
        Args:
            params: Parâmetros atuais (pode ser None)
            default_preset: Preset a usar se datas não forem fornecidas
        
        Returns:
            Params com dataInicial e dataFinal garantidos
        """
        if params is None:
            params = {}
        
        # Se já tem as duas datas, retorna sem modificar
        if "dataInicial" in params and "dataFinal" in params:
            if params["dataInicial"] and params["dataFinal"]:
                return params
        
        # Aplica range padrão
        default_range = cls.resolve(default_preset)
        result = dict(params)  # Cópia
        
        # Aplica dataInicial se não existir ou for None
        if "dataInicial" not in result or not result["dataInicial"]:
            result["dataInicial"] = default_range.start
        
        # Aplica dataFinal se não existir ou for None
        if "dataFinal" not in result or not result["dataFinal"]:
            result["dataFinal"] = default_range.end
        
        return result
