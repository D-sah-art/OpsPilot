from abc import ABC, abstractmethod
from typing import List
from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from ..models import Incident

class CorrelationStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def correlate(
        self,
        alerts: List[Alert],
        graph: DependencyGraph,
        time_window_seconds: float = 600.0,
        threshold: float = 0.45
    ) -> List[Incident]:
        """
        Executes correlation strategy on alerts using topology.
        Returns a deterministic list of Incident objects.
        """
        pass
