"""
plant.py - Tracks a single plant's health over a series of readings
(photos), and raises simple threshold-based alerts.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from vision import compute_health_metrics, HealthMetrics


@dataclass
class Reading:
    timestamp: datetime
    metrics: HealthMetrics
    source: str  # e.g. filename the reading came from


@dataclass
class Alert:
    timestamp: datetime
    message: str
    severity: str  # "warning" | "critical"


class PlantMonitor:
    """
    Accumulates readings for one plant and flags simple, explainable
    alerts: a low health score, or a sudden jump in brown/necrotic
    tissue between consecutive readings.
    """

    def __init__(self, name: str,
                 warning_score: float = 60.0,
                 critical_score: float = 35.0,
                 brown_jump_threshold: float = 10.0):
        self.name = name
        self.warning_score = warning_score
        self.critical_score = critical_score
        self.brown_jump_threshold = brown_jump_threshold

        self.history: List[Reading] = []
        self.alerts: List[Alert] = []

    def add_reading(self, image_rgb, source: str = "", timestamp: Optional[datetime] = None) -> Reading:
        metrics = compute_health_metrics(image_rgb)
        reading = Reading(
            timestamp=timestamp or datetime.now(),
            metrics=metrics,
            source=source,
        )
        self._check_alerts(reading)
        self.history.append(reading)
        return reading

    def _check_alerts(self, reading: Reading) -> None:
        score = reading.metrics.health_score

        if score < self.critical_score:
            self.alerts.append(Alert(
                timestamp=reading.timestamp,
                message=f"{self.name}: health score critically low ({score:.1f})",
                severity="critical",
            ))
        elif score < self.warning_score:
            self.alerts.append(Alert(
                timestamp=reading.timestamp,
                message=f"{self.name}: health score below warning threshold ({score:.1f})",
                severity="warning",
            ))

        if self.history:
            prev_brown = self.history[-1].metrics.brown_pct
            delta = reading.metrics.brown_pct - prev_brown
            if delta >= self.brown_jump_threshold:
                self.alerts.append(Alert(
                    timestamp=reading.timestamp,
                    message=(
                        f"{self.name}: necrotic/brown tissue increased by "
                        f"{delta:.1f} percentage points since the last reading"
                    ),
                    severity="warning",
                ))

    def latest(self) -> Optional[Reading]:
        return self.history[-1] if self.history else None

    def trend(self) -> List[float]:
        """Health score over time, oldest first."""
        return [r.metrics.health_score for r in self.history]
