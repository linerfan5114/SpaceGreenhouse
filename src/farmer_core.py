#!/usr/bin/env python3
"""
SpaceGreenhouse - Zero-G Farmer Core Module
NASA ISS Plant Habitat Automation System
Author: SpaceGreenhouse Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum, IntEnum
import time
import json


class PlantSpecies(IntEnum):
    LETTUCE = 0
    TOMATO = 1
    WHEAT = 2
    RADISH = 3
    ARABIDOPSIS = 4
    BASIL = 5
    KALE = 6
    PEPPER = 7
    STRAWBERRY = 8
    SOYBEAN = 9
    POTATO = 10
    RICE = 11


class GrowthStage(IntEnum):
    SEED = 0
    GERMINATION = 1
    SEEDLING = 2
    VEGETATIVE = 3
    BUDDING = 4
    FLOWERING = 5
    FRUITING = 6
    MATURE = 7
    SENESCENCE = 8


class HealthStatus(IntEnum):
    EXCELLENT = 0
    GOOD = 1
    FAIR = 2
    STRESSED = 3
    DISEASED = 4
    CRITICAL = 5
    DEAD = 6


@dataclass
class SpectralSignature:
    red: float
    green: float
    blue: float
    nir: float
    red_edge: float
    swir1: float
    swir2: float
    timestamp: float = 0.0

    def ndvi(self) -> float:
        if self.nir + self.red == 0:
            return 0.0
        return (self.nir - self.red) / (self.nir + self.red)

    def pri(self) -> float:
        if self.green + self.blue == 0:
            return 0.0
        return (self.green - self.blue) / (self.green + self.blue)

    def ci(self) -> float:
        if self.nir + self.red_edge == 0:
            return 0.0
        return (self.nir / self.red_edge) - 1.0 if self.red_edge > 0 else 0.0

    def wbi(self) -> float:
        if self.swir1 + self.nir == 0:
            return 0.0
        return self.swir1 / self.nir if self.nir > 0 else 0.0

    def health_score(self) -> float:
        ndvi_val = self.ndvi()
        pri_val = self.pri()
        if 0.6 <= ndvi_val <= 0.95:
            ndvi_score = 1.0
        elif 0.3 <= ndvi_val < 0.6:
            ndvi_score = 0.6
        else:
            ndvi_score = 0.3
        pri_score = min(max(pri_val / 0.05, 0.0), 1.0) if pri_val > 0 else 0.5
        return (ndvi_score * 0.6 + pri_score * 0.4)


@dataclass
class RootZone:
    moisture: float = 0.65
    ph_level: float = 6.2
    ec_level: float = 1.4
    temperature: float = 22.0
    oxygen_level: float = 8.5
    nitrogen_ppm: float = 150.0
    phosphorus_ppm: float = 50.0
    potassium_ppm: float = 200.0
    calcium_ppm: float = 120.0
    magnesium_ppm: float = 40.0

    def is_optimal(self) -> bool:
        return (0.55 <= self.moisture <= 0.75 and
                5.8 <= self.ph_level <= 6.5 and
                1.0 <= self.ec_level <= 2.0 and
                19.0 <= self.temperature <= 24.0 and
                self.oxygen_level >= 6.0)


@dataclass
class Plant:
    id: int
    species: PlantSpecies
    position: Tuple[float, float, float]
    growth_stage: GrowthStage = GrowthStage.SEED
    health: HealthStatus = HealthStatus.GOOD
    spectral: SpectralSignature = field(default_factory=lambda: SpectralSignature(0, 0, 0, 0, 0, 0, 0))
    roots: RootZone = field(default_factory=RootZone)
    height_cm: float = 0.0
    leaf_area_cm2: float = 0.0
    biomass_g: float = 0.0
    age_days: float = 0.0
    water_uptake_ml_per_day: float = 0.0
    nutrient_uptake_mg_per_day: float = 0.0
    fruit_count: int = 0
    pollination_attempts: int = 0
    disease_probability: float = 0.0
    disease_type: str = "none"

    def update_growth_stage(self):
        if self.height_cm < 0.5:
            self.growth_stage = GrowthStage.SEED
        elif self.height_cm < 2.0:
            self.growth_stage = GrowthStage.GERMINATION
        elif self.height_cm < 8.0:
            self.growth_stage = GrowthStage.SEEDLING
        elif self.height_cm < 15.0:
            self.growth_stage = GrowthStage.VEGETATIVE
        elif self.height_cm < 20.0:
            self.growth_stage = GrowthStage.BUDDING
        elif self.fruit_count == 0:
            self.growth_stage = GrowthStage.FLOWERING
        elif self.fruit_count < 5:
            self.growth_stage = GrowthStage.FRUITING
        elif self.age_days > 90:
            self.growth_stage = GrowthStage.SENESCENCE
        else:
            self.growth_stage = GrowthStage.MATURE


@dataclass
class EnvironmentData:
    temperature_c: float = 22.0
    humidity_pct: float = 60.0
    co2_ppm: float = 800.0
    o2_pct: float = 21.0
    pressure_kpa: float = 101.3
    light_intensity_lux: float = 25000.0
    light_spectrum: Tuple[float, float, float, float, float] = (0.3, 0.25, 0.2, 0.15, 0.1)
    radiation_uSv_per_h: float = 0.5
    vibration_m_per_s2: float = 0.01
    air_flow_m_per_s: float = 0.5


@dataclass
class WaterSystem:
    reservoir_ml: float = 5000.0
    ph_level: float = 6.0
    ec_level: float = 1.2
    temperature_c: float = 21.0
    flow_rate_ml_per_min: float = 100.0
    filter_health_pct: float = 100.0
    uv_sterilizer_active: bool = True
    pump_active: bool = False
    total_dispensed_ml: float = 0.0


class FarmerCore:
    def __init__(self, config_path: Optional[str] = None):
        self.plants: List[Plant] = []
        self.environment = EnvironmentData()
        self.water_system = WaterSystem()
        self.mission_time: float = 0.0
        self.cycle_count: int = 0
        self.config = self._load_config(config_path)
        self._init_plants()

    def _load_config(self, path: Optional[str]) -> Dict[str, Any]:
        default_config = {
            "greenhouse_volume_m3": 2.5,
            "max_plants": 24,
            "growth_cycle_hours": 12,
            "dark_cycle_hours": 12,
            "pollination_interval_hours": 8,
            "harvest_readiness_threshold": 0.85,
            "disease_scan_interval_hours": 4,
            "nutrient_check_interval_hours": 6,
            "water_check_interval_hours": 1,
            "emergency_temp_max_c": 35.0,
            "emergency_temp_min_c": 10.0,
            "emergency_humidity_max_pct": 95.0,
            "emergency_humidity_min_pct": 25.0,
        }
        if path:
            try:
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except FileNotFoundError:
                pass
        return default_config

    def _init_plants(self):
        max_plants = self.config.get("max_plants", 24)
        species_list = list(PlantSpecies)
        rows = int(np.ceil(np.sqrt(max_plants)))
        cols = int(np.ceil(max_plants / rows))
        spacing_x = 30.0
        spacing_y = 30.0
        plant_id = 0
        for row in range(rows):
            for col in range(cols):
                if plant_id >= max_plants:
                    break
                species = species_list[plant_id % len(species_list)]
                x = col * spacing_x
                y = row * spacing_y
                z = 0.0
                plant = Plant(
                    id=plant_id,
                    species=species,
                    position=(x, y, z),
                )
                self.plants.append(plant)
                plant_id += 1

    def update_environment(self, dt_hours: float):
        self.environment.temperature_c += np.random.normal(0, 0.1) * dt_hours
        self.environment.temperature_c = np.clip(
            self.environment.temperature_c,
            self.config["emergency_temp_min_c"],
            self.config["emergency_temp_max_c"]
        )
        self.environment.humidity_pct += np.random.normal(0, 0.5) * dt_hours
        self.environment.humidity_pct = np.clip(
            self.environment.humidity_pct,
            self.config["emergency_humidity_min_pct"],
            self.config["emergency_humidity_max_pct"]
        )
        self.environment.co2_ppm += np.random.normal(0, 10) * dt_hours
        self.environment.co2_ppm = max(400.0, min(2000.0, self.environment.co2_ppm))

    def update_plant_growth(self, plant: Plant, dt_hours: float):
        env_factor = self._calculate_environment_factor()
        water_factor = self._calculate_water_factor(plant)
        nutrient_factor = self._calculate_nutrient_factor(plant)
        health_factor = self._calculate_health_factor(plant)
        growth_rate = 0.15 * env_factor * water_factor * nutrient_factor * health_factor
        plant.height_cm += growth_rate * dt_hours * 24
        plant.leaf_area_cm2 += growth_rate * dt_hours * 24 * 2.5
        plant.biomass_g += growth_rate * dt_hours * 24 * 0.5
        plant.water_uptake_ml_per_day = 15.0 * env_factor * water_factor
        plant.nutrient_uptake_mg_per_day = 5.0 * env_factor * nutrient_factor
        plant.age_days += dt_hours / 24.0
        plant.roots.moisture -= plant.water_uptake_ml_per_day * dt_hours / 24.0 / 100.0
        plant.roots.moisture = max(0.0, min(1.0, plant.roots.moisture))
        plant.update_growth_stage()
        self._update_plant_health(plant, dt_hours)

    def _calculate_environment_factor(self) -> float:
        temp_opt = 22.0
        temp_tolerance = 5.0
        temp_factor = np.exp(-((self.environment.temperature_c - temp_opt) ** 2) /
                             (2 * temp_tolerance ** 2))
        hum_opt = 60.0
        hum_tolerance = 15.0
        hum_factor = np.exp(-((self.environment.humidity_pct - hum_opt) ** 2) /
                            (2 * hum_tolerance ** 2))
        light_factor = min(self.environment.light_intensity_lux / 25000.0, 1.0)
        return temp_factor * 0.4 + hum_factor * 0.3 + light_factor * 0.3

    def _calculate_water_factor(self, plant: Plant) -> float:
        if plant.roots.moisture < 0.2:
            return plant.roots.moisture / 0.2
        elif plant.roots.moisture > 0.9:
            return max(0.5, 1.0 - (plant.roots.moisture - 0.9) / 0.1)
        return 1.0

    def _calculate_nutrient_factor(self, plant: Plant) -> float:
        factors = []
        targets = {
            'nitrogen': (150.0, 50.0),
            'phosphorus': (50.0, 20.0),
            'potassium': (200.0, 80.0),
        }
        values = {
            'nitrogen': plant.roots.nitrogen_ppm,
            'phosphorus': plant.roots.phosphorus_ppm,
            'potassium': plant.roots.potassium_ppm,
        }
        for nutrient, (target, tolerance) in targets.items():
            val = values[nutrient]
            if val < target - tolerance:
                factors.append(val / (target - tolerance) if target > tolerance else 0.5)
            elif val > target + tolerance:
                factors.append(max(0.5, 1.0 - (val - target - tolerance) / tolerance))
            else:
                factors.append(1.0)
        return np.mean(factors)

    def _calculate_health_factor(self, plant: Plant) -> float:
        health_map = {
            HealthStatus.EXCELLENT: 1.0,
            HealthStatus.GOOD: 0.9,
            HealthStatus.FAIR: 0.7,
            HealthStatus.STRESSED: 0.5,
            HealthStatus.DISEASED: 0.3,
            HealthStatus.CRITICAL: 0.1,
            HealthStatus.DEAD: 0.0,
        }
        return health_map.get(plant.health, 0.5)

    def _update_plant_health(self, plant: Plant, dt_hours: float):
        if plant.roots.moisture < 0.1:
            plant.health = HealthStatus.CRITICAL
            return
        if plant.disease_probability > 0.6:
            plant.health = HealthStatus.DISEASED
            return
        if plant.disease_probability > 0.3:
            plant.health = HealthStatus.STRESSED
            return
        if plant.roots.ph_level < 4.5 or plant.roots.ph_level > 8.0:
            plant.health = HealthStatus.STRESSED
            return
        spectral_health = plant.spectral.health_score()
        if spectral_health > 0.85:
            plant.health = HealthStatus.EXCELLENT
        elif spectral_health > 0.7:
            plant.health = HealthStatus.GOOD
        elif spectral_health > 0.5:
            plant.health = HealthStatus.FAIR
        else:
            plant.health = HealthStatus.STRESSED

    def water_plants(self):
        for plant in self.plants:
            if plant.health != HealthStatus.DEAD:
                needed = min(200.0, max(20.0, plant.water_uptake_ml_per_day / 24.0))
                if self.water_system.reservoir_ml >= needed:
                    self.water_system.reservoir_ml -= needed
                    self.water_system.total_dispensed_ml += needed
                    plant.roots.moisture = min(1.0, plant.roots.moisture + needed / 500.0)
                    self.water_system.pump_active = True

    def check_emergency(self) -> List[str]:
        alerts = []
        if self.environment.temperature_c > self.config["emergency_temp_max_c"]:
            alerts.append(f"CRITICAL: Temperature {self.environment.temperature_c:.1f}C exceeds maximum")
        if self.environment.temperature_c < self.config["emergency_temp_min_c"]:
            alerts.append(f"CRITICAL: Temperature {self.environment.temperature_c:.1f}C below minimum")
        if self.environment.humidity_pct > self.config["emergency_humidity_max_pct"]:
            alerts.append(f"WARNING: Humidity {self.environment.humidity_pct:.1f}% exceeds maximum")
        if self.water_system.reservoir_ml < 500.0:
            alerts.append(f"WARNING: Water reservoir low ({self.water_system.reservoir_ml:.0f}ml)")
        dead_count = sum(1 for p in self.plants if p.health == HealthStatus.DEAD)
        if dead_count > len(self.plants) * 0.3:
            alerts.append(f"CRITICAL: {dead_count} plants dead")
        return alerts

    def get_status_report(self) -> Dict[str, Any]:
        species_counts = {}
        stage_counts = {}
        health_counts = {}
        for plant in self.plants:
            species_name = plant.species.name
            species_counts[species_name] = species_counts.get(species_name, 0) + 1
            stage_name = plant.growth_stage.name
            stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
            health_name = plant.health.name
            health_counts[health_name] = health_counts.get(health_name, 0) + 1
        return {
            "mission_time_hours": self.mission_time,
            "cycle_count": self.cycle_count,
            "total_plants": len(self.plants),
            "species_distribution": species_counts,
            "growth_stages": stage_counts,
            "health_status": health_counts,
            "environment": {
                "temperature_c": self.environment.temperature_c,
                "humidity_pct": self.environment.humidity_pct,
                "co2_ppm": self.environment.co2_ppm,
                "light_lux": self.environment.light_intensity_lux,
            },
            "water_system": {
                "reservoir_ml": self.water_system.reservoir_ml,
                "ph": self.water_system.ph_level,
                "total_dispensed_ml": self.water_system.total_dispensed_ml,
            },
            "alerts": self.check_emergency(),
        }

    def save_state(self, filepath: str):
        state = {
            "mission_time": self.mission_time,
            "cycle_count": self.cycle_count,
            "environment": {
                "temperature_c": self.environment.temperature_c,
                "humidity_pct": self.environment.humidity_pct,
                "co2_ppm": self.environment.co2_ppm,
            },
            "water_reservoir_ml": self.water_system.reservoir_ml,
            "total_dispensed_ml": self.water_system.total_dispensed_ml,
            "plants": []
        }
        for plant in self.plants:
            state["plants"].append({
                "id": plant.id,
                "species": plant.species.name,
                "growth_stage": plant.growth_stage.name,
                "health": plant.health.name,
                "height_cm": plant.height_cm,
                "leaf_area_cm2": plant.leaf_area_cm2,
                "biomass_g": plant.biomass_g,
                "age_days": plant.age_days,
                "fruit_count": plant.fruit_count,
                "disease_probability": plant.disease_probability,
            })
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def run_cycle(self, dt_hours: float = 1.0):
        self.mission_time += dt_hours
        self.cycle_count += 1
        self.update_environment(dt_hours)
        for plant in self.plants:
            self.update_plant_growth(plant, dt_hours)
        if self.cycle_count % 6 == 0:
            self.water_plants()
        alerts = self.check_emergency()
        return alerts