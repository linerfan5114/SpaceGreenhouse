#!/usr/bin/env python3
"""
SpaceGreenhouse - Automated Harvesting System
Computer vision ripeness detection & robotic picking
NASA ISS Food Production Module - Zero-G compatible harvesting
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from enum import IntEnum
import time
from collections import deque


class FruitStage(IntEnum):
    FRUIT_SET = 0
    IMMATURE_GREEN = 1
    MATURE_GREEN = 2
    BREAKER = 3
    TURNING = 4
    PINK = 5
    LIGHT_RED = 6
    RED_RIPE = 7
    OVER_RIPE = 8
    ROTTEN = 9


class Quality(IntEnum):
    PREMIUM_A = 0
    STANDARD_B = 1
    PROCESSING_C = 2
    COMPOST_D = 3
    SEED_RECOVERY = 4


@dataclass
class Fruit:
    fruit_id: int
    plant_id: int
    position: Tuple[float, float, float]
    species: str = "tomato"
    stage: FruitStage = FruitStage.FRUIT_SET
    weight_g: float = 0.0
    diameter_cm: float = 0.0
    color_rgb: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    sugar_content_brix: float = 0.0
    firmness: float = 1.0
    days_since_fruit_set: float = 0.0
    harvestable: bool = False
    quality: Quality = Quality.PROCESSING_C
    harvested_at: float = 0.0


@dataclass
class HarvesterArm:
    arm_length_cm: float = 40.0
    gripper_width_cm: float = 8.0
    tip_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    gripper_open: bool = True
    fruit_held: Optional[int] = None
    is_moving: bool = False
    movement_speed_cm_per_s: float = 8.0
    cutting_tool_active: bool = False
    sterilization_active: bool = True


@dataclass
class HarvestRecord:
    timestamp: float
    fruit_id: int
    plant_id: int
    species: str
    weight_g: float
    quality: Quality
    ripeness_stage: FruitStage
    sugar_content_brix: float
    firmness: float
    stem_cut_clean: bool
    damage_free: bool


@dataclass
class HarvestBin:
    bin_id: int
    quality_level: Quality
    capacity_kg: float = 5.0
    current_weight_kg: float = 0.0
    fruits: List[int] = field(default_factory=list)
    sealed: bool = False
    sterilization_applied: bool = True


class Harvester:
    def __init__(self):
        self.fruits: Dict[int, Fruit] = {}
        self.arm = HarvesterArm()
        self.records: List[HarvestRecord] = []
        self.bins: List[HarvestBin] = []
        self.fruit_id_counter = 0
        self.total_harvested_kg = 0.0
        self.harvest_efficiency = 0.95
        self.damage_rate = 0.02
        self.ripeness_thresholds = {
            "tomato": (FruitStage.PINK, FruitStage.RED_RIPE),
            "pepper": (FruitStage.TURNING, FruitStage.RED_RIPE),
            "strawberry": (FruitStage.LIGHT_RED, FruitStage.RED_RIPE),
            "lettuce": (FruitStage.MATURE_GREEN, FruitStage.MATURE_GREEN),
        }
        self._init_bins()

    def _init_bins(self):
        self.bins = [
            HarvestBin(bin_id=1, quality_level=Quality.PREMIUM_A),
            HarvestBin(bin_id=2, quality_level=Quality.STANDARD_B),
            HarvestBin(bin_id=3, quality_level=Quality.PROCESSING_C),
            HarvestBin(bin_id=4, quality_level=Quality.COMPOST_D),
            HarvestBin(bin_id=5, quality_level=Quality.SEED_RECOVERY),
        ]

    def register_fruit(self, plant_id: int, position: Tuple[float, float, float],
                       species: str = "tomato") -> int:
        self.fruit_id_counter += 1
        fruit = Fruit(
            fruit_id=self.fruit_id_counter,
            plant_id=plant_id,
            position=position,
            species=species,
        )
        self.fruits[self.fruit_id_counter] = fruit
        return self.fruit_id_counter

    def update_fruit_development(self, fruit_id: int, days_since_set: float,
                                 temperature_c: float = 22.0):
        if fruit_id not in self.fruits:
            return
        fruit = self.fruits[fruit_id]
        fruit.days_since_fruit_set = days_since_set
        growth_rate = 1.0 + (temperature_c - 20.0) * 0.05
        if fruit.stage <= FruitStage.MATURE_GREEN:
            fruit.weight_g += 0.5 * growth_rate
            fruit.diameter_cm += 0.05 * growth_rate
        if fruit.species == "tomato":
            self._update_tomato_ripeness(fruit, days_since_set)
        elif fruit.species == "pepper":
            self._update_pepper_ripeness(fruit, days_since_set)
        elif fruit.species == "strawberry":
            self._update_strawberry_ripeness(fruit, days_since_set)
        else:
            self._update_generic_ripeness(fruit, days_since_set)
        self._update_quality(fruit)
        self._check_harvestable(fruit)

    def _update_tomato_ripeness(self, fruit: Fruit, days: float):
        stages = [
            (0, FruitStage.FRUIT_SET),
            (5, FruitStage.IMMATURE_GREEN),
            (15, FruitStage.MATURE_GREEN),
            (20, FruitStage.BREAKER),
            (23, FruitStage.TURNING),
            (25, FruitStage.PINK),
            (27, FruitStage.LIGHT_RED),
            (30, FruitStage.RED_RIPE),
        ]
        for threshold, stage in stages:
            if days >= threshold:
                fruit.stage = stage
        if days > 35:
            fruit.stage = FruitStage.OVER_RIPE
        if days > 45:
            fruit.stage = FruitStage.ROTTEN
        self._update_color_from_stage(fruit)

    def _update_pepper_ripeness(self, fruit: Fruit, days: float):
        if days < 10:
            fruit.stage = FruitStage.IMMATURE_GREEN
        elif days < 25:
            fruit.stage = FruitStage.MATURE_GREEN
        elif days < 30:
            fruit.stage = FruitStage.TURNING
        elif days < 35:
            fruit.stage = FruitStage.RED_RIPE
        elif days < 45:
            fruit.stage = FruitStage.OVER_RIPE
        else:
            fruit.stage = FruitStage.ROTTEN
        self._update_color_from_stage(fruit)

    def _update_strawberry_ripeness(self, fruit: Fruit, days: float):
        if days < 5:
            fruit.stage = FruitStage.IMMATURE_GREEN
        elif days < 8:
            fruit.stage = FruitStage.MATURE_GREEN
        elif days < 10:
            fruit.stage = FruitStage.LIGHT_RED
        elif days < 12:
            fruit.stage = FruitStage.RED_RIPE
        elif days < 15:
            fruit.stage = FruitStage.OVER_RIPE
        else:
            fruit.stage = FruitStage.ROTTEN
        self._update_color_from_stage(fruit)

    def _update_generic_ripeness(self, fruit: Fruit, days: float):
        if days < 10:
            fruit.stage = FruitStage.IMMATURE_GREEN
        elif days < 20:
            fruit.stage = FruitStage.MATURE_GREEN
        elif days < 25:
            fruit.stage = FruitStage.TURNING
        elif days < 30:
            fruit.stage = FruitStage.RED_RIPE
        elif days < 38:
            fruit.stage = FruitStage.OVER_RIPE
        else:
            fruit.stage = FruitStage.ROTTEN
        self._update_color_from_stage(fruit)

    def _update_color_from_stage(self, fruit: Fruit):
        color_map = {
            FruitStage.FRUIT_SET: (0.0, 0.9, 0.0),
            FruitStage.IMMATURE_GREEN: (0.1, 0.85, 0.1),
            FruitStage.MATURE_GREEN: (0.2, 0.8, 0.1),
            FruitStage.BREAKER: (0.6, 0.5, 0.0),
            FruitStage.TURNING: (0.8, 0.3, 0.0),
            FruitStage.PINK: (0.9, 0.15, 0.0),
            FruitStage.LIGHT_RED: (0.95, 0.05, 0.0),
            FruitStage.RED_RIPE: (1.0, 0.0, 0.0),
            FruitStage.OVER_RIPE: (0.7, 0.05, 0.05),
            FruitStage.ROTTEN: (0.3, 0.1, 0.05),
        }
        fruit.color_rgb = color_map.get(fruit.stage, (0.0, 1.0, 0.0))
        fruit.sugar_content_brix = 3.0 + fruit.stage * 0.8 if fruit.stage <= FruitStage.RED_RIPE else 4.5
        fruit.firmness = max(0.1, 1.0 - fruit.stage * 0.1)

    def _update_quality(self, fruit: Fruit):
        if fruit.stage == FruitStage.RED_RIPE and fruit.firmness > 0.7:
            fruit.quality = Quality.PREMIUM_A
        elif fruit.stage in [FruitStage.LIGHT_RED, FruitStage.RED_RIPE]:
            fruit.quality = Quality.STANDARD_B
        elif fruit.stage in [FruitStage.TURNING, FruitStage.PINK]:
            fruit.quality = Quality.PROCESSING_C
        elif fruit.stage in [FruitStage.OVER_RIPE, FruitStage.ROTTEN]:
            fruit.quality = Quality.COMPOST_D
        else:
            fruit.quality = Quality.PROCESSING_C

    def _check_harvestable(self, fruit: Fruit):
        thresholds = self.ripeness_thresholds.get(fruit.species,
            (FruitStage.TURNING, FruitStage.RED_RIPE))
        fruit.harvestable = thresholds[0] <= fruit.stage <= thresholds[1]

    def _calculate_distance(self, p1: Tuple[float, float, float],
                            p2: Tuple[float, float, float]) -> float:
        return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)

    def find_harvestable_fruits(self) -> List[int]:
        harvestable = []
        for fid, fruit in self.fruits.items():
            if fruit.harvestable and fruit.stage != FruitStage.ROTTEN:
                harvestable.append(fid)
        return sorted(harvestable, key=lambda f: self.fruits[f].stage, reverse=True)

    def move_arm_to_fruit(self, fruit_id: int) -> bool:
        if fruit_id not in self.fruits:
            return False
        fruit = self.fruits[fruit_id]
        self.arm.tip_position = fruit.position
        self.arm.is_moving = True
        self.arm.gripper_open = True
        time.sleep(0.005)
        self.arm.is_moving = False
        return True

    def harvest_fruit(self, fruit_id: int) -> Optional[HarvestRecord]:
        if fruit_id not in self.fruits:
            return None
        fruit = self.fruits[fruit_id]
        if not fruit.harvestable:
            return None
        self.move_arm_to_fruit(fruit_id)
        self.arm.gripper_open = False
        self.arm.fruit_held = fruit_id
        self.arm.cutting_tool_active = True
        stem_cut_clean = np.random.random() > 0.05
        damage_free = np.random.random() > self.damage_rate
        if damage_free and stem_cut_clean:
            real_quality = fruit.quality
        else:
            real_quality = Quality(max(int(fruit.quality) + 1, Quality.COMPOST_D))
        record = HarvestRecord(
            timestamp=time.time(),
            fruit_id=fruit_id,
            plant_id=fruit.plant_id,
            species=fruit.species,
            weight_g=fruit.weight_g,
            quality=real_quality,
            ripeness_stage=fruit.stage,
            sugar_content_brix=fruit.sugar_content_brix,
            firmness=fruit.firmness,
            stem_cut_clean=stem_cut_clean,
            damage_free=damage_free,
        )
        self.records.append(record)
        self._place_in_bin(fruit_id, real_quality, fruit.weight_g)
        fruit.harvested_at = time.time()
        self.total_harvested_kg += fruit.weight_g / 1000.0
        self.arm.gripper_open = True
        self.arm.fruit_held = None
        self.arm.cutting_tool_active = False
        return record

    def _place_in_bin(self, fruit_id: int, quality: Quality, weight_g: float):
        for bin in self.bins:
            if bin.quality_level == quality:
                if bin.current_weight_kg + weight_g / 1000.0 <= bin.capacity_kg:
                    bin.fruits.append(fruit_id)
                    bin.current_weight_kg += weight_g / 1000.0
                    return
        compost_bin = self.bins[-1]
        compost_bin.fruits.append(fruit_id)
        compost_bin.current_weight_kg += weight_g / 1000.0

    def harvest_all_ready(self) -> Dict:
        ready = self.find_harvestable_fruits()
        results = {"total_ready": len(ready), "harvested": 0, "failed": 0,
                   "total_weight_kg": 0.0, "quality_distribution": {}}
        for fid in ready:
            record = self.harvest_fruit(fid)
            if record:
                results["harvested"] += 1
                results["total_weight_kg"] += record.weight_g / 1000.0
                quality_name = record.quality.name
                results["quality_distribution"][quality_name] = \
                    results["quality_distribution"].get(quality_name, 0) + 1
            else:
                results["failed"] += 1
        return results

    def detect_overripe(self) -> List[int]:
        overripe = []
        for fid, fruit in self.fruits.items():
            if fruit.stage in [FruitStage.OVER_RIPE, FruitStage.ROTTEN]:
                overripe.append(fid)
        return overripe

    def clean_compost(self) -> int:
        removed = 0
        for fid in self.detect_overripe():
            fruit = self.fruits[fid]
            self._place_in_bin(fid, Quality.COMPOST_D, fruit.weight_g)
            fruit.harvested_at = time.time()
            removed += 1
        return removed

    def get_harvest_statistics(self) -> Dict:
        total_harvested = len(self.records)
        if total_harvested == 0:
            return {"total_harvested": 0, "total_weight_kg": 0.0,
                    "avg_weight_g": 0.0, "quality_distribution": {},
                    "avg_sugar_brix": 0.0, "damage_rate": 0.0}
        quality_dist = {}
        for record in self.records:
            quality_name = record.quality.name
            quality_dist[quality_name] = quality_dist.get(quality_name, 0) + 1
        avg_weight = np.mean([r.weight_g for r in self.records])
        avg_sugar = np.mean([r.sugar_content_brix for r in self.records])
        damage_count = sum(1 for r in self.records if not r.damage_free)
        return {
            "total_harvested": total_harvested,
            "total_weight_kg": self.total_harvested_kg,
            "avg_weight_g": avg_weight,
            "quality_distribution": quality_dist,
            "avg_sugar_brix": avg_sugar,
            "damage_rate": damage_count / total_harvested if total_harvested > 0 else 0.0,
            "bin_status": {f"bin_{b.bin_id}_{b.quality_level.name}":
                          f"{b.current_weight_kg:.2f}kg" for b in self.bins},
        }

    def predict_next_harvest(self) -> Dict[str, float]:
        future_harvest = {}
        for fid, fruit in self.fruits.items():
            if fruit.stage < FruitStage.TURNING:
                species = fruit.species
                if species not in future_harvest:
                    future_harvest[species] = 0.0
                future_harvest[species] += fruit.weight_g / 1000.0
        return future_harvest

    def sterilize_equipment(self):
        self.arm.sterilization_active = True
        for bin in self.bins:
            bin.sterilization_applied = True