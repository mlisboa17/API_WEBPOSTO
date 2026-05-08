from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class DomainEvent:
    """Base class para todos os domain events."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_name: str = field(default="")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""

    def __post_init__(self):
        if not self.event_name:
            self.event_name = self.__class__.__name__
