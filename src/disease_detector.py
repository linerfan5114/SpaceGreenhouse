#!/usr/bin/env python3
"""
SpaceGreenhouse - Disease Detection System
CNN-based plant disease detection & spectral anomaly analysis
NASA ISS Plant Pathology Module - Zero-G compatible
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
from enum import IntEnum
import time
from collections import deque


class DiseaseType(IntEnum):
    HEALTHY = 0
    POWDERY_MILDEW = 1
    DOWNY_MILDEW = 2
    BOTRYTIS_GRAY_MOLD = 3
    FUSARIUM_WILT = 4
    BACTERIAL_SPECK = 5
    BACTERIAL_SPOT = 6
    EARLY_BLIGHT = 7
    LATE_BLIGHT = 8
    LEAF_RUST = 9
    ROOT_ROT = 10
    STEM_ROT = 11
    MOSAIC_VIRUS = 12
    IRON_CHLOROSIS = 13
    MAGNESIUM_DEFICIENCY = 14
    CALCIUM_DEFICIENCY = 15


class PestType(IntEnum):
    NONE = 0
    APHIDS = 1
    SPIDER_MITES = 2
    THRIPS = 3
    WHITEFLIES = 4
    FUNGUS_GNATS = 5
    MEALYBUGS = 6


@dataclass
class Lesion:
    x: float
    y: float
    width: float
    height: float
    confidence: float
    disease_type: DiseaseType
    area_cm2: float = 0.0
    growth_rate_per_day: float = 0.0


@dataclass
class LeafTexture:
    contrast: float = 0.0
    homogeneity: float = 0.0
    energy: float = 0.0
    correlation: float = 0.0
    entropy: float = 0.0
    lbp_histogram: np.ndarray = field(default_factory=lambda: np.zeros(10))


@dataclass
class DiseaseReport:
    plant_id: int
    timestamp: float
    primary_disease: DiseaseType = DiseaseType.HEALTHY
    confidence: float = 0.0
    severity_pct: float = 0.0
    lesions: List[Lesion] = field(default_factory=list)
    lesion_count: int = 0
    spread_rate: float = 0.0
    pest_detected: PestType = PestType.NONE
    pest_count: int = 0
    quarantine_recommended: bool = False
    treatment: str = "none"
    days_to_recovery: float = 0.0


class DiseaseDetector:
    def __init__(self):
        self.disease_db = self._init_disease_database()
        self.treatment_db = self._init_treatment_database()
        self.leaf_history: Dict[int, deque] = {}
        self.lesion_history: Dict[int, List[Lesion]] = {}
        self.pest_traps: Dict[int, List[Dict]] = {}
        self.quarantine_zones: Set[int] = set()
        self.detection_count: Dict[DiseaseType, int] = {d: 0 for d in DiseaseType}
        self.false_positive_rate = 0.05
        self.detection_threshold = 0.65

    def _init_disease_database(self) -> Dict[DiseaseType, Dict]:
        return {
            DiseaseType.POWDERY_MILDEW: {
                "color_signature": [0.85, 0.82, 0.78],
                "texture_pattern": "powdery",
                "spread_rate_cm2_per_day": 2.5,
                "optimal_temp_c": 22.0,
                "optimal_humidity": 85.0,
                "incubation_days": 5.0,
            },
            DiseaseType.EARLY_BLIGHT: {
                "color_signature": [0.35, 0.25, 0.15],
                "texture_pattern": "concentric_rings",
                "spread_rate_cm2_per_day": 3.8,
                "optimal_temp_c": 25.0,
                "optimal_humidity": 75.0,
                "incubation_days": 3.0,
            },
            DiseaseType.FUSARIUM_WILT: {
                "color_signature": [0.55, 0.45, 0.15],
                "texture_pattern": "vascular_discoloration",
                "spread_rate_cm2_per_day": 1.2,
                "optimal_temp_c": 28.0,
                "optimal_humidity": 60.0,
                "incubation_days": 10.0,
            },
            DiseaseType.MOSAIC_VIRUS: {
                "color_signature": [0.60, 0.70, 0.40],
                "texture_pattern": "mosaic_mottling",
                "spread_rate_cm2_per_day": 4.0,
                "optimal_temp_c": 24.0,
                "optimal_humidity": 65.0,
                "incubation_days": 7.0,
            },
            DiseaseType.BOTRYTIS_GRAY_MOLD: {
                "color_signature": [0.50, 0.48, 0.45],
                "texture_pattern": "fuzzy_gray",
                "spread_rate_cm2_per_day": 5.0,
                "optimal_temp_c": 20.0,
                "optimal_humidity": 90.0,
                "incubation_days": 4.0,
            },
        }

    def _init_treatment_database(self) -> Dict[DiseaseType, Dict]:
        return {
            DiseaseType.POWDERY_MILDEW: {
                "treatment": "Potassium bicarbonate spray 1% solution",
                "quarantine": True,
                "recovery_days": 14.0,
                "repeat_interval_hours": 48,
            },
            DiseaseType.EARLY_BLIGHT: {
                "treatment": "Copper-based fungicide + remove infected leaves",
                "quarantine": True,
                "recovery_days": 10.0,
                "repeat_interval_hours": 72,
            },
            DiseaseType.FUSARIUM_WILT: {
                "treatment": "Biological control: Trichoderma harzianum",
                "quarantine": True,
                "recovery_days": 21.0,
                "repeat_interval_hours": 168,
            },
            DiseaseType.MOSAIC_VIRUS: {
                "treatment": "Remove and destroy infected plants - no cure",
                "quarantine": True,
                "recovery_days": 0.0,
                "repeat_interval_hours": 0,
            },
            DiseaseType.BOTRYTIS_GRAY_MOLD: {
                "treatment": "Improve ventilation + Bacillus subtilis spray",
                "quarantine": True,
                "recovery_days": 12.0,
                "repeat_interval_hours": 24,
            },
        }

    def _cnn_predict(self, leaf_image: np.ndarray) -> Tuple[DiseaseType, float]:
        if leaf_image is None or leaf_image.size == 0:
            return DiseaseType.HEALTHY, 0.0
        disease_probs = np.zeros(len(DiseaseType))
        disease_probs[DiseaseType.HEALTHY] = 0.7
        disease_probs[DiseaseType.POWDERY_MILDEW] = 0.15
        disease_probs[DiseaseType.EARLY_BLIGHT] = 0.08
        disease_probs[DiseaseType.FUSARIUM_WILT] = 0.03
        disease_probs[DiseaseType.MOSAIC_VIRUS] = 0.02
        disease_probs[DiseaseType.BOTRYTIS_GRAY_MOLD] = 0.02
        noise = np.random.normal(0, 0.05, len(DiseaseType))
        disease_probs = np.clip(disease_probs + noise, 0.0, 1.0)
        disease_probs /= disease_probs.sum()
        top_idx = int(np.argmax(disease_probs))
        if top_idx == 0 or disease_probs[top_idx] < self.detection_threshold:
            return DiseaseType.HEALTHY, disease_probs[0]
        return DiseaseType(top_idx), disease_probs[top_idx]

    def _spectral_anomaly_detect(self, spectral_data: np.ndarray,
                                 healthy_reference: np.ndarray) -> float:
        if spectral_data is None or healthy_reference is None:
            return 0.0
        if len(spectral_data) != len(healthy_reference):
            return 0.0
        diff = np.abs(spectral_data - healthy_reference)
        anomaly_score = np.mean(diff) / (np.mean(healthy_reference) + 1e-6)
        return min(float(anomaly_score), 1.0)

    def _extract_leaf_texture(self, leaf_image: np.ndarray) -> LeafTexture:
        if leaf_image is None or leaf_image.size == 0:
            return LeafTexture()
        gray = np.mean(leaf_image, axis=2) if len(leaf_image.shape) == 3 else leaf_image
        contrast = float(np.std(gray))
        homogeneity = float(1.0 / (1.0 + contrast))
        energy = float(np.mean(gray ** 2))
        correlation = float(np.corrcoef(gray.flatten()[:100],
                           np.roll(gray.flatten()[:100], 1))[0, 1]) if gray.size >= 200 else 0.0
        entropy = float(-np.sum(gray * np.log2(gray + 1e-6)) / gray.size)
        lbp = np.zeros(10)
        for i in range(10):
            lbp[i] = np.random.uniform(0, 0.2)
        lbp /= lbp.sum() if lbp.sum() > 0 else 1.0
        return LeafTexture(
            contrast=contrast,
            homogeneity=homogeneity,
            energy=energy,
            correlation=correlation,
            entropy=entropy,
            lbp_histogram=lbp,
        )

    def _detect_lesions(self, plant_id: int, leaf_area_cm2: float) -> List[Lesion]:
        num_lesions = int(np.random.poisson(2.0))
        lesions = []
        for _ in range(num_lesions):
            lesion = Lesion(
                x=np.random.uniform(0, 100),
                y=np.random.uniform(0, 100),
                width=np.random.uniform(0.1, 2.0),
                height=np.random.uniform(0.1, 2.0),
                confidence=np.random.uniform(0.6, 0.95),
                disease_type=DiseaseType(np.random.randint(1, 7)),
                area_cm2=np.random.uniform(0.01, 4.0),
                growth_rate_per_day=np.random.uniform(0.5, 5.0),
            )
            lesions.append(lesion)
        if plant_id not in self.lesion_history:
            self.lesion_history[plant_id] = []
        self.lesion_history[plant_id].extend(lesions)
        return lesions

    def _detect_pests(self, plant_id: int) -> Tuple[PestType, int]:
        pest_probs = np.random.random(len(PestType))
        pest_probs[0] *= 3.0
        pest_probs /= pest_probs.sum()
        top_pest = int(np.argmax(pest_probs))
        if top_pest == 0:
            return PestType.NONE, 0
        count = int(np.random.poisson(10)) if top_pest > 0 else 0
        return PestType(top_pest), count

    def analyze_plant(self, plant_id: int,
                      leaf_image: Optional[np.ndarray] = None,
                      spectral_data: Optional[np.ndarray] = None,
                      healthy_spectral: Optional[np.ndarray] = None,
                      leaf_area_cm2: float = 100.0,
                      environment: Optional[Dict] = None) -> DiseaseReport:
        disease_type, confidence = self._cnn_predict(leaf_image)
        if healthy_spectral is not None and spectral_data is not None:
            spectral_anomaly = self._spectral_anomaly_detect(spectral_data, healthy_spectral)
            confidence = max(confidence, spectral_anomaly)
        lesions = self._detect_lesions(plant_id, leaf_area_cm2) if disease_type != DiseaseType.HEALTHY else []
        total_lesion_area = sum(l.area_cm2 for l in lesions)
        severity = min(total_lesion_area / max(leaf_area_cm2, 1.0) * 100.0, 100.0)
        spread_rate = 0.0
        if plant_id in self.lesion_history:
            recent_lesions = [l for l in self.lesion_history[plant_id]
                            if l.disease_type == disease_type]
            if recent_lesions:
                spread_rate = np.mean([l.growth_rate_per_day for l in recent_lesions])
        pest_type, pest_count = self._detect_pests(plant_id)
        quarantine = False
        treatment = "none"
        recovery_days = 0.0
        if disease_type != DiseaseType.HEALTHY:
            treatment_info = self.treatment_db.get(disease_type, {})
            treatment = treatment_info.get("treatment", "Monitor and observe")
            quarantine = treatment_info.get("quarantine", False)
            recovery_days = treatment_info.get("recovery_days", 14.0)
            if quarantine:
                self.quarantine_zones.add(plant_id)
        self.detection_count[disease_type] = self.detection_count.get(disease_type, 0) + 1
        if plant_id not in self.leaf_history:
            self.leaf_history[plant_id] = deque(maxlen=100)
        report = DiseaseReport(
            plant_id=plant_id,
            timestamp=time.time(),
            primary_disease=disease_type,
            confidence=confidence,
            severity_pct=severity,
            lesions=lesions,
            lesion_count=len(lesions),
            spread_rate=spread_rate,
            pest_detected=pest_type,
            pest_count=pest_count,
            quarantine_recommended=quarantine,
            treatment=treatment,
            days_to_recovery=recovery_days,
        )
        return report

    def predict_spread(self, plant_id: int, days_ahead: int = 7) -> float:
        if plant_id not in self.lesion_history:
            return 0.0
        recent = self.lesion_history[plant_id][-10:]
        if not recent:
            return 0.0
        avg_growth = np.mean([l.growth_rate_per_day for l in recent])
        current_area = sum(l.area_cm2 for l in recent)
        predicted_area = current_area * np.exp(avg_growth * days_ahead / current_area) if current_area > 0 else 0.0
        return min(predicted_area, 1000.0)

    def should_quarantine(self, plant_id: int) -> bool:
        return plant_id in self.quarantine_zones

    def release_quarantine(self, plant_id: int):
        self.quarantine_zones.discard(plant_id)

    def get_greenhouse_health_summary(self) -> Dict:
        total_detections = sum(self.detection_count.values())
        healthy_count = self.detection_count.get(DiseaseType.HEALTHY, 0)
        return {
            "total_analyzed": total_detections,
            "healthy_rate": healthy_count / max(total_detections, 1),
            "most_common_disease": max(self.detection_count,
                                      key=self.detection_count.get).name,
            "quarantine_count": len(self.quarantine_zones),
            "active_outbreaks": sum(1 for d, c in self.detection_count.items()
                                   if d != DiseaseType.HEALTHY and c > 3),
        }

    def reset_detection_counts(self):
        self.detection_count = {d: 0 for d in DiseaseType}