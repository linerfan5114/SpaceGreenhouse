#!/usr/bin/env python3
"""
SpaceGreenhouse - Plant Health Monitor
Hyperspectral Imaging & Environmental Stress Detection
NASA ISS Plant Habitat Monitoring System
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
from enum import IntEnum
import time


class StressType(IntEnum):
    NONE = 0
    WATER_DEFICIT = 1
    WATER_EXCESS = 2
    NITROGEN_DEFICIENCY = 3
    PHOSPHORUS_DEFICIENCY = 4
    POTASSIUM_DEFICIENCY = 5
    IRON_DEFICIENCY = 6
    MAGNESIUM_DEFICIENCY = 7
    LIGHT_STRESS = 8
    TEMPERATURE_STRESS = 9
    CO2_STRESS = 10
    PATHOGEN_INFECTION = 11
    RADIATION_DAMAGE = 12


@dataclass
class HyperspectralReading:
    wavelengths_nm: np.ndarray
    reflectance: np.ndarray
    timestamp: float = 0.0
    plant_id: int = 0

    def get_band(self, wl_min: float, wl_max: float) -> float:
        mask = (self.wavelengths_nm >= wl_min) & (self.wavelengths_nm <= wl_max)
        if np.any(mask):
            return float(np.mean(self.reflectance[mask]))
        return 0.0

    def ndvi(self) -> float:
        nir = self.get_band(750, 900)
        red = self.get_band(620, 700)
        if nir + red == 0:
            return 0.0
        return (nir - red) / (nir + red)

    def pri(self) -> float:
        green = self.get_band(530, 570)
        blue = self.get_band(430, 490)
        if green + blue == 0:
            return 0.0
        return (green - blue) / (green + blue)

    def ci_rededge(self) -> float:
        nir = self.get_band(750, 900)
        red_edge = self.get_band(700, 730)
        if red_edge == 0:
            return 0.0
        return (nir / red_edge) - 1.0

    def wbi(self) -> float:
        swir = self.get_band(1500, 1750)
        nir = self.get_band(750, 900)
        if nir == 0:
            return 0.0
        return swir / nir

    def sipi(self) -> float:
        nir = self.get_band(750, 900)
        blue = self.get_band(430, 490)
        if nir - blue == 0:
            return 0.0
        return (nir - blue) / (nir - red) if (nir - red) != 0 else 0.0

    def ari(self) -> float:
        green = self.get_band(530, 570)
        red_edge = self.get_band(700, 730)
        if green + red_edge == 0:
            return 0.0
        return (1.0 / green - 1.0 / red_edge) if green > 0 and red_edge > 0 else 0.0


@dataclass
class ThermalReading:
    leaf_temp_c: float = 22.0
    ambient_temp_c: float = 22.0
    canopy_temp_c: float = 22.0
    temp_variance: float = 0.0
    timestamp: float = 0.0

    def crop_water_stress_index(self) -> float:
        if self.ambient_temp_c == self.leaf_temp_c:
            return 0.0
        return (self.leaf_temp_c - self.ambient_temp_c) / max(self.leaf_temp_c, 1.0)


@dataclass
class NutrientProfile:
    nitrogen_idx: float = 1.0
    phosphorus_idx: float = 1.0
    potassium_idx: float = 1.0
    iron_idx: float = 1.0
    magnesium_idx: float = 1.0
    calcium_idx: float = 1.0
    sulfur_idx: float = 1.0
    zinc_idx: float = 1.0
    manganese_idx: float = 1.0
    boron_idx: float = 1.0
    copper_idx: float = 1.0
    overall_health: float = 1.0

    def most_deficient(self) -> str:
        nutrients = {
            "Nitrogen": self.nitrogen_idx,
            "Phosphorus": self.phosphorus_idx,
            "Potassium": self.potassium_idx,
            "Iron": self.iron_idx,
            "Magnesium": self.magnesium_idx,
            "Calcium": self.calcium_idx,
        }
        return min(nutrients, key=nutrients.get)


@dataclass
class PlantHealthReport:
    plant_id: int
    timestamp: float
    ndvi: float = 0.0
    pri: float = 0.0
    ci: float = 0.0
    wbi: float = 0.0
    lai: float = 0.0
    cwsi: float = 0.0
    stress_type: StressType = StressType.NONE
    stress_severity: float = 0.0
    nutrient_profile: NutrientProfile = field(default_factory=NutrientProfile)
    growth_rate_cm_per_day: float = 0.0
    photosynthetic_efficiency: float = 0.0
    chlorophyll_content_mg_per_m2: float = 0.0
    yield_prediction_pct: float = 0.0


class PlantMonitor:
    def __init__(self):
        self.readings_history: Dict[int, List[HyperspectralReading]] = {}
        self.thermal_history: Dict[int, List[ThermalReading]] = {}
        self.growth_history: Dict[int, List[float]] = {}
        self.spectral_library = self._init_spectral_library()
        self.stress_thresholds = {
            StressType.WATER_DEFICIT: {"wbi_max": 0.8, "cwsi_min": 0.3},
            StressType.NITROGEN_DEFICIENCY: {"ndvi_min": 0.4, "pri_max": -0.05},
            StressType.LIGHT_STRESS: {"pri_min": -0.1, "ndvi_max": 0.85},
            StressType.PATHOGEN_INFECTION: {"ndvi_drop_rate": 0.05},
        }

    def _init_spectral_library(self) -> Dict[str, np.ndarray]:
        return {
            "healthy_lettuce": np.array([0.05, 0.15, 0.08, 0.10, 0.55, 0.25, 0.15]),
            "stressed_lettuce": np.array([0.08, 0.20, 0.12, 0.08, 0.35, 0.30, 0.20]),
            "healthy_tomato": np.array([0.04, 0.12, 0.06, 0.08, 0.60, 0.22, 0.12]),
            "stressed_tomato": np.array([0.07, 0.18, 0.10, 0.06, 0.40, 0.28, 0.18]),
        }

    def capture_hyperspectral(self, plant_id: int) -> HyperspectralReading:
        wavelengths = np.linspace(400, 1800, 200)
        base_reflectance = np.zeros(200)
        base_reflectance[20:60] = np.random.normal(0.1, 0.02, 40)
        base_reflectance[60:100] = np.random.normal(0.15, 0.03, 40)
        base_reflectance[100:140] = np.random.normal(0.5, 0.05, 40)
        base_reflectance[140:170] = np.random.normal(0.3, 0.04, 30)
        base_reflectance[170:] = np.random.normal(0.15, 0.03, 30)
        base_reflectance = np.clip(base_reflectance, 0.0, 1.0)
        reading = HyperspectralReading(
            wavelengths_nm=wavelengths,
            reflectance=base_reflectance,
            timestamp=time.time(),
            plant_id=plant_id,
        )
        if plant_id not in self.readings_history:
            self.readings_history[plant_id] = []
        self.readings_history[plant_id].append(reading)
        return reading

    def capture_thermal(self, plant_id: int, ambient_temp: float) -> ThermalReading:
        leaf_temp = ambient_temp + np.random.normal(-1.5, 1.5)
        canopy_temp = leaf_temp + np.random.normal(-0.5, 0.5)
        reading = ThermalReading(
            leaf_temp_c=leaf_temp,
            ambient_temp_c=ambient_temp,
            canopy_temp_c=canopy_temp,
            temp_variance=np.random.uniform(0.1, 1.5),
            timestamp=time.time(),
        )
        if plant_id not in self.thermal_history:
            self.thermal_history[plant_id] = []
        self.thermal_history[plant_id].append(reading)
        return reading

    def calculate_lai(self, plant_id: int, leaf_area_cm2: float, canopy_radius_cm: float = 15.0) -> float:
        if canopy_radius_cm <= 0:
            return 0.0
        ground_area = np.pi * canopy_radius_cm ** 2
        if ground_area <= 0:
            return 0.0
        return leaf_area_cm2 / ground_area

    def calculate_chlorophyll(self, reading: HyperspectralReading) -> float:
        red = reading.get_band(620, 700)
        nir = reading.get_band(750, 900)
        red_edge = reading.get_band(700, 730)
        if red == 0:
            return 0.0
        cl_index = (nir / red - 1.0) * (red_edge / nir if nir > 0 else 0)
        return max(0.0, cl_index * 500.0)

    def detect_stress(self, plant_id: int) -> Tuple[StressType, float]:
        if plant_id not in self.readings_history or not self.readings_history[plant_id]:
            return StressType.NONE, 0.0
        current = self.readings_history[plant_id][-1]
        ndvi_val = current.ndvi()
        pri_val = current.pri()
        wbi_val = current.wbi()
        cwsi_val = 0.0
        if plant_id in self.thermal_history and self.thermal_history[plant_id]:
            cwsi_val = self.thermal_history[plant_id][-1].crop_water_stress_index()
        candidates = []
        if wbi_val > self.stress_thresholds[StressType.WATER_DEFICIT]["wbi_max"]:
            severity = min(1.0, (wbi_val - 0.8) / 0.4)
            candidates.append((StressType.WATER_DEFICIT, severity))
        if cwsi_val > self.stress_thresholds[StressType.WATER_DEFICIT]["cwsi_min"]:
            severity = min(1.0, cwsi_val / 0.5)
            candidates.append((StressType.WATER_DEFICIT, severity))
        if ndvi_val < self.stress_thresholds[StressType.NITROGEN_DEFICIENCY]["ndvi_min"]:
            severity = min(1.0, (0.4 - ndvi_val) / 0.4)
            candidates.append((StressType.NITROGEN_DEFICIENCY, severity))
        if len(self.readings_history[plant_id]) >= 2:
            prev_ndvi = self.readings_history[plant_id][-2].ndvi()
            ndvi_drop = prev_ndvi - ndvi_val
            if ndvi_drop > self.stress_thresholds[StressType.PATHOGEN_INFECTION]["ndvi_drop_rate"]:
                severity = min(1.0, ndvi_drop * 10.0)
                candidates.append((StressType.PATHOGEN_INFECTION, severity))
        if not candidates:
            return StressType.NONE, 0.0
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]

    def analyze_nutrients(self, reading: HyperspectralReading) -> NutrientProfile:
        profile = NutrientProfile()
        profile.nitrogen_idx = np.clip(reading.get_band(550, 570) / max(reading.get_band(650, 680), 0.01), 0.0, 2.0)
        profile.phosphorus_idx = np.clip(reading.get_band(430, 450) / max(reading.get_band(550, 570), 0.01), 0.0, 2.0)
        profile.potassium_idx = np.clip(reading.get_band(450, 470) / max(reading.get_band(680, 700), 0.01), 0.0, 2.0)
        profile.iron_idx = np.clip(reading.get_band(510, 530) / max(reading.get_band(550, 570), 0.01), 0.0, 2.0)
        profile.magnesium_idx = np.clip(reading.get_band(470, 490) / max(reading.get_band(550, 570), 0.01), 0.0, 2.0)
        profile.calcium_idx = np.clip(reading.get_band(490, 510) / max(reading.get_band(550, 570), 0.01), 0.0, 2.0)
        nutrient_values = [
            profile.nitrogen_idx, profile.phosphorus_idx, profile.potassium_idx,
            profile.iron_idx, profile.magnesium_idx, profile.calcium_idx,
            profile.sulfur_idx, profile.zinc_idx, profile.manganese_idx,
            profile.boron_idx, profile.copper_idx,
        ]
        profile.overall_health = np.mean([min(v, 1.0) for v in nutrient_values])
        return profile

    def predict_yield(self, plant_id: int, current_biomass: float, target_biomass: float,
                      days_remaining: float, health_score: float) -> float:
        if target_biomass <= 0 or days_remaining <= 0:
            return 0.0
        growth_ratio = current_biomass / target_biomass
        expected_ratio = min(1.0, growth_ratio + health_score * 0.05 * days_remaining)
        return expected_ratio * 100.0

    def generate_report(self, plant_id: int, plant_data: Dict[str, Any]) -> PlantHealthReport:
        reading = self.capture_hyperspectral(plant_id)
        thermal = self.capture_thermal(plant_id, plant_data.get("ambient_temp_c", 22.0))
        stress_type, stress_severity = self.detect_stress(plant_id)
        nutrient_profile = self.analyze_nutrients(reading)
        lai = self.calculate_lai(plant_id, plant_data.get("leaf_area_cm2", 0.0))
        chlorophyll = self.calculate_chlorophyll(reading)
        growth_rate = 0.0
        if plant_id in self.growth_history and len(self.growth_history[plant_id]) >= 2:
            growth_rate = (self.growth_history[plant_id][-1] -
                          self.growth_history[plant_id][-2]) * 24.0
        yield_pred = self.predict_yield(
            plant_id,
            plant_data.get("biomass_g", 0.0),
            plant_data.get("target_biomass_g", 100.0),
            plant_data.get("days_remaining", 60.0),
            plant_data.get("health_score", 0.8),
        )
        report = PlantHealthReport(
            plant_id=plant_id,
            timestamp=time.time(),
            ndvi=reading.ndvi(),
            pri=reading.pri(),
            ci=reading.ci_rededge(),
            wbi=reading.wbi(),
            lai=lai,
            cwsi=thermal.crop_water_stress_index(),
            stress_type=stress_type,
            stress_severity=stress_severity,
            nutrient_profile=nutrient_profile,
            growth_rate_cm_per_day=growth_rate,
            photosynthetic_efficiency=reading.pri(),
            chlorophyll_content_mg_per_m2=chlorophyll,
            yield_prediction_pct=yield_pred,
        )
        return report

    def track_growth(self, plant_id: int, height_cm: float):
        if plant_id not in self.growth_history:
            self.growth_history[plant_id] = []
        self.growth_history[plant_id].append(height_cm)
        if len(self.growth_history[plant_id]) > 168:
            self.growth_history[plant_id].pop(0)