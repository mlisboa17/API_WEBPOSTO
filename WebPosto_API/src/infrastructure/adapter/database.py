from decimal import Decimal

from sqlalchemy import Numeric, Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr

Base = declarative_base()


def Numeric12_4(name=None, nullable=False, default=Decimal("0.0000")):
    """Helper factory to create a NUMERIC(12,4) column type for SQLAlchemy models."""
    return Column(Numeric(12, 4, asdecimal=True), nullable=nullable, default=default)


class BaseModelMixin:
    """Mixin to provide consistent table naming and metadata."""

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


__all__ = ["Base", "Numeric12_4", "BaseModelMixin"]
