#!/usr/bin/env python3
"""
SpaceGreenhouse - Automated Pollination System
Buzz Pollination & Flower Detection in Microgravity
NASA ISS Zero-G compatible pollination robotics
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
from enum import IntEnum
import time


class FlowerStage(IntEnum):
    BUD = 0
    OPENING = 1
    FULL_BLOOM = 2
    RECEPTIVE = 3
    POLLINATED = 4
    WITHERING = 5
    FRUIT_SET = 6


class PollenSource(IntEnum):
    SAME_FLOWER = 0
    SAME_PLANT = 1
    NEIGHBOR_PLANT = 2
    STORED_POLLEN = 3
    CROSS_SPECIES = 4


@dataclass
class Flower:
    flower_id: int
    plant_id: int
    position: Tuple[float, float, float]
    stage: FlowerStage = FlowerStage.BUD
    petal_count: int = 5
    corolla_diameter_cm: float = 1.0
    nectar_present: bool = False
    pollen_viability: float = 1.0
    stigma_receptive: bool = False
    last_visited: float = 0.0
    visit_count: int = 0
    pollination_success: bool = False


@dataclass
class PollenGrain:
    grain_id: int
    source_plant_id: int
    source_flower_id: int
    viability: float = 1.0
    age_hours: float = 0.0
    size_um: float = 25.0
    genetic_markers: str = "wild_type"
    storage_temp_c: float = 4.0


@dataclass
class PollenBank:
    grains: List[PollenGrain] = field(default_factory=list)
    capacity: int = 10000
    temperature_c: float = 4.0
    humidity_pct: float = 30.0
    sterilization_active: bool = True

    def store(self, grain: PollenGrain) -> bool:
        if len(self.grains) >= self.capacity:
            return False
        self.grains.append(grain)
        return True

    def retrieve(self, source_plant_id: int) -> Optional[PollenGrain]:
        viable = [g for g in self.grains
                  if g.viability > 0.5 and g.source_plant_id == source_plant_id]
        if not viable:
            viable = [g for g in self.grains if g.viability > 0.3]
        if not viable:
            return None
        best = max(viable, key=lambda g: g.viability)
        self.grains.remove(best)
        return best

    def degrade_over_time(self, dt_hours: float):
        for grain in self.grains:
            grain.age_hours += dt_hours
            grain.viability *= np.exp(-0.02 * dt_hours)
            grain.viability = max(0.0, grain.viability)
        self.grains = [g for g in self.grains if g.viability > 0.05]


@dataclass
class PollinatorArm:
    arm_length_cm: float = 30.0
    tip_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    vibration_frequency_hz: float = 0.0
    vibration_amplitude_um: float = 0.0
    brush_attached: bool = True
    pollen_collected: bool = False
    current_target: Optional[int] = None
    is_moving: bool = False
    movement_speed_cm_per_s: float = 5.0


@dataclass
class PollinationRecord:
    timestamp: float
    flower_id: int
    plant_id: int
    pollen_source: PollenSource
    vibration_freq_hz: float
    vibration_duration_s: float
    success: bool
    pollen_grains_deposited: int


class PollinationSystem:
    def __init__(self):
        self.flowers: Dict[int, Flower] = {}
        self.pollen_bank = PollenBank()
        self.arm = PollinatorArm()
        self.records: List[PollinationRecord] = []
        self.flower_id_counter = 0
        self.optimal_frequencies = {
            "default": 350.0,
            "tomato": 400.0,
            "pepper": 380.0,
            "strawberry": 320.0,
            "eggplant": 450.0,
        }

    def register_flower(self, plant_id: int, position: Tuple[float, float, float],
                        species: str = "default") -> int:
        self.flower_id_counter += 1
        flower = Flower(
            flower_id=self.flower_id_counter,
            plant_id=plant_id,
            position=position,
        )
        self.flowers[self.flower_id_counter] = flower
        return self.flower_id_counter

    def update_flower_stage(self, flower_id: int, age_days: float,
                            is_flowering: bool = True):
        if flower_id not in self.flowers:
            return
        flower = self.flowers[flower_id]
        if not is_flowering:
            flower.stage = FlowerStage.BUD
            return
        if age_days < 2.0:
            flower.stage = FlowerStage.BUD
        elif age_days < 3.0:
            flower.stage = FlowerStage.OPENING
        elif age_days < 6.0:
            flower.stage = FlowerStage.FULL_BLOOM
            flower.stigma_receptive = age_days > 4.0
        elif age_days < 8.0:
            flower.stage = FlowerStage.RECEPTIVE
            flower.stigma_receptive = True
        elif flower.pollination_success:
            flower.stage = FlowerStage.FRUIT_SET
        else:
            flower.stage = FlowerStage.WITHERING
            flower.pollen_viability *= 0.8
        if flower.stage in [FlowerStage.FULL_BLOOM, FlowerStage.RECEPTIVE]:
            flower.nectar_present = np.random.random() > 0.3

    def _calculate_distance(self, p1: Tuple[float, float, float],
                            p2: Tuple[float, float, float]) -> float:
        return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)

    def find_ready_flowers(self, plant_id: Optional[int] = None) -> List[int]:
        ready = []
        for fid, flower in self.flowers.items():
            if plant_id is not None and flower.plant_id != plant_id:
                continue
            if flower.stage in [FlowerStage.FULL_BLOOM, FlowerStage.RECEPTIVE]:
                if flower.stigma_receptive:
                    ready.append(fid)
        return sorted(ready, key=lambda fid: self.flowers[fid].last_visited)

    def move_arm_to_flower(self, flower_id: int) -> bool:
        if flower_id not in self.flowers:
            return False
        flower = self.flowers[flower_id]
        distance = self._calculate_distance(self.arm.tip_position, flower.position)
        travel_time = distance / max(self.arm.movement_speed_cm_per_s, 0.1)
        self.arm.tip_position = flower.position
        self.arm.current_target = flower_id
        self.arm.is_moving = True
        time.sleep(0.01)
        self.arm.is_moving = False
        return True

    def buzz_pollinate(self, flower_id: int, species: str = "default",
                       duration_s: float = 3.0) -> bool:
        if flower_id not in self.flowers:
            return False
        flower = self.flowers[flower_id]
        if flower.stage not in [FlowerStage.FULL_BLOOM, FlowerStage.RECEPTIVE]:
            return False
        if not flower.stigma_receptive:
            return False
        freq = self.optimal_frequencies.get(species, self.optimal_frequencies["default"])
        self.arm.vibration_frequency_hz = freq
        self.arm.vibration_amplitude_um = 200.0
        time.sleep(0.001 * duration_s)
        pollen_released = int(np.random.uniform(50, 200))
        pollen_deposited = int(pollen_released * np.random.uniform(0.3, 0.7))
        flower.pollination_success = True
        flower.stage = FlowerStage.POLLINATED
        flower.visit_count += 1
        flower.last_visited = time.time()
        self.arm.vibration_frequency_hz = 0.0
        self.arm.vibration_amplitude_um = 0.0
        record = PollinationRecord(
            timestamp=time.time(),
            flower_id=flower_id,
            plant_id=flower.plant_id,
            pollen_source=PollenSource.SAME_FLOWER,
            vibration_freq_hz=freq,
            vibration_duration_s=duration_s,
            success=True,
            pollen_grains_deposited=pollen_deposited,
        )
        self.records.append(record)
        return True

    def cross_pollinate(self, source_flower_id: int, target_flower_id: int,
                        species: str = "default") -> bool:
        if source_flower_id not in self.flowers or target_flower_id not in self.flowers:
            return False
        source = self.flowers[source_flower_id]
        target = self.flowers[target_flower_id]
        if source.stage not in [FlowerStage.FULL_BLOOM, FlowerStage.RECEPTIVE]:
            return False
        if target.stage not in [FlowerStage.FULL_BLOOM, FlowerStage.RECEPTIVE]:
            return False
        if not target.stigma_receptive:
            return False
        grain = PollenGrain(
            grain_id=int(time.time() * 1000),
            source_plant_id=source.plant_id,
            source_flower_id=source_flower_id,
            viability=source.pollen_viability,
        )
        self.pollen_bank.store(grain)
        self.move_arm_to_flower(source_flower_id)
        self.arm.pollen_collected = True
        self.move_arm_to_flower(target_flower_id)
        success = self.buzz_pollinate(target_flower_id, species, duration_s=2.0)
        if success:
            self.records[-1].pollen_source = PollenSource.NEIGHBOR_PLANT
        self.arm.pollen_collected = False
        return success

    def pollinate_with_stored_pollen(self, flower_id: int,
                                     source_plant_id: int,
                                     species: str = "default") -> bool:
        if flower_id not in self.flowers:
            return False
        grain = self.pollen_bank.retrieve(source_plant_id)
        if grain is None:
            return False
        self.move_arm_to_flower(flower_id)
        success = self.buzz_pollinate(flower_id, species, duration_s=2.5)
        if success and self.records:
            self.records[-1].pollen_source = PollenSource.STORED_POLLEN
        return success

    def auto_pollinate_all(self, plants: List[Dict], species: str = "default") -> Dict:
        results = {"attempted": 0, "successful": 0, "skipped": 0}
        ready_flowers = self.find_ready_flowers()
        results["attempted"] = len(ready_flowers)
        for fid in ready_flowers:
            self.move_arm_to_flower(fid)
            if self.buzz_pollinate(fid, species, duration_s=3.0):
                results["successful"] += 1
            else:
                results["skipped"] += 1
        return results

    def get_unpollinated_count(self) -> int:
        return sum(1 for f in self.flowers.values()
                   if f.stage in [FlowerStage.FULL_BLOOM, FlowerStage.RECEPTIVE]
                   and f.stigma_receptive)

    def get_pollination_rate(self) -> float:
        total_flowers = len(self.flowers)
        if total_flowers == 0:
            return 0.0
        pollinated = sum(1 for f in self.flowers.values()
                        if f.stage in [FlowerStage.POLLINATED, FlowerStage.FRUIT_SET])
        return pollinated / total_flowers

    def get_statistics(self) -> Dict:
        total = len(self.records)
        if total == 0:
            return {"total_pollinations": 0, "success_rate": 0.0,
                    "avg_duration_s": 0.0, "avg_frequency_hz": 0.0}
        successful = sum(1 for r in self.records if r.success)
        avg_duration = np.mean([r.vibration_duration_s for r in self.records])
        avg_freq = np.mean([r.vibration_freq_hz for r in self.records])
        return {
            "total_pollinations": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "avg_duration_s": avg_duration,
            "avg_frequency_hz": avg_freq,
            "pollen_bank_grains": len(self.pollen_bank.grains),
            "avg_pollen_viability": np.mean([g.viability for g in self.pollen_bank.grains])
            if self.pollen_bank.grains else 0.0,
            "unpollinated_flowers": self.get_unpollinated_count(),
        }