#!/usr/bin/env python3
"""
SpaceGreenhouse - Main Simulation
NASA ISS Plant Habitat - Fully Autonomous Operation
Integrates: FarmerCore, PlantMonitor, Pollinator, DiseaseDetector, Harvester
"""

import numpy as np
import time
import json
from datetime import datetime
from typing import Dict, Any
from collections import deque

from farmer_core import FarmerCore, PlantSpecies, GrowthStage, HealthStatus
from plant_monitor import PlantMonitor, StressType
from pollinator import PollinationSystem, FlowerStage
from disease_detector import DiseaseDetector, DiseaseType
from harvester import Harvester, FruitStage, Quality


class SpaceGreenhouseSimulator:
    def __init__(self, config_path: str = None):
        self.farmer = FarmerCore(config_path)
        self.monitor = PlantMonitor()
        self.pollinator = PollinationSystem()
        self.detector = DiseaseDetector()
        self.harvester = Harvester()

        self.simulation_time_hours = 0.0
        self.simulation_days = 0
        self.cycle_count = 0
        self.dt_hours = 1.0

        self.event_log = deque(maxlen=1000)
        self.alert_log = deque(maxlen=200)
        self.harvest_log = deque(maxlen=500)

        self.stats = {
            "total_water_used_ml": 0.0,
            "total_harvests": 0,
            "total_diseases_detected": 0,
            "total_pollinations": 0,
            "emergency_events": 0,
            "crop_yield_total_kg": 0.0,
        }

        self._init_flowers_for_plants()

    def _init_flowers_for_plants(self):
        for plant in self.farmer.plants:
            if plant.species in [PlantSpecies.TOMATO, PlantSpecies.PEPPER,
                                 PlantSpecies.STRAWBERRY]:
                for i in range(np.random.randint(3, 8)):
                    pos = (plant.position[0] + np.random.uniform(-5, 5),
                           plant.position[1] + np.random.uniform(-5, 5),
                           plant.position[2] + plant.height_cm / 2.0)
                    self.pollinator.register_flower(plant.id, pos, plant.species.name.lower())

    def _log_event(self, event_type: str, message: str):
        self.event_log.append({
            "time_hours": self.simulation_time_hours,
            "day": self.simulation_days,
            "type": event_type,
            "message": message,
        })

    def _check_alerts(self):
        alerts = self.farmer.check_emergency()
        if alerts:
            for alert in alerts:
                self.alert_log.append({
                    "time_hours": self.simulation_time_hours,
                    "alert": alert,
                })
                self._log_event("ALERT", alert)
                if "CRITICAL" in alert:
                    self.stats["emergency_events"] += 1

    def _run_plant_monitoring(self):
        for plant in self.farmer.plants:
            if plant.health == HealthStatus.DEAD:
                continue
            plant_data = {
                "ambient_temp_c": self.farmer.environment.temperature_c,
                "leaf_area_cm2": plant.leaf_area_cm2,
                "biomass_g": plant.biomass_g,
                "target_biomass_g": 200.0,
                "days_remaining": max(1.0, 90.0 - plant.age_days),
                "health_score": 1.0 - plant.disease_probability,
            }
            report = self.monitor.generate_report(plant.id, plant_data)
            self.monitor.track_growth(plant.id, plant.height_cm)
            if report.stress_type != StressType.NONE and report.stress_severity > 0.6:
                plant.health = HealthStatus.STRESSED
                self._log_event("STRESS",
                    f"Plant {plant.id} ({plant.species.name}): "
                    f"{report.stress_type.name} severity {report.stress_severity:.2f}")

    def _run_disease_detection(self):
        for plant in self.farmer.plants:
            if plant.health == HealthStatus.DEAD:
                continue
            if self.cycle_count % 4 == 0:
                report = self.detector.analyze_plant(
                    plant.id,
                    leaf_area_cm2=plant.leaf_area_cm2,
                    environment={
                        "temperature_c": self.farmer.environment.temperature_c,
                        "humidity_pct": self.farmer.environment.humidity_pct,
                    }
                )
                if report.primary_disease != DiseaseType.HEALTHY:
                    plant.disease_probability = report.confidence
                    plant.disease_type = report.primary_disease.name
                    self.stats["total_diseases_detected"] += 1
                    self._log_event("DISEASE",
                        f"Plant {plant.id}: {report.primary_disease.name} "
                        f"(confidence: {report.confidence:.2f}, severity: {report.severity_pct:.1f}%)")
                    if report.quarantine_recommended:
                        self._log_event("QUARANTINE",
                            f"Plant {plant.id} quarantined - {report.treatment}")

    def _run_pollination(self):
        if self.cycle_count % 8 == 0:
            for plant in self.farmer.plants:
                if plant.species not in [PlantSpecies.TOMATO, PlantSpecies.PEPPER,
                                         PlantSpecies.STRAWBERRY]:
                    continue
                if plant.growth_stage not in [GrowthStage.FLOWERING, GrowthStage.FRUITING]:
                    continue
                if plant.health in [HealthStatus.DISEASED, HealthStatus.CRITICAL, HealthStatus.DEAD]:
                    continue
                ready = self.pollinator.find_ready_flowers(plant.id)
                if ready:
                    for fid in ready:
                        flower = self.pollinator.flowers.get(fid)
                        if flower and flower.stage in [FlowerStage.FULL_BLOOM, FlowerStage.RECEPTIVE]:
                            success = self.pollinator.buzz_pollinate(
                                fid, plant.species.name.lower(), duration_s=3.0)
                            if success:
                                plant.pollination_attempts += 1
                                self.stats["total_pollinations"] += 1
                                self._log_event("POLLINATION",
                                    f"Plant {plant.id} flower {fid} pollinated successfully")

    def _update_fruit_development(self):
        for plant in self.farmer.plants:
            if plant.species not in [PlantSpecies.TOMATO, PlantSpecies.PEPPER,
                                     PlantSpecies.STRAWBERRY]:
                continue
            if plant.growth_stage == GrowthStage.FRUITING:
                if plant.fruit_count == 0 and plant.pollination_attempts > 0:
                    for _ in range(np.random.randint(3, 10)):
                        pos = (plant.position[0] + np.random.uniform(-8, 8),
                               plant.position[1] + np.random.uniform(-8, 8),
                               plant.position[2] + np.random.uniform(5, 15))
                        fid = self.harvester.register_fruit(
                            plant.id, pos, plant.species.name.lower())
                        self.harvester.update_fruit_development(
                            fid, np.random.uniform(10, 35),
                            self.farmer.environment.temperature_c)
                    plant.fruit_count = len([f for f in self.harvester.fruits.values()
                                            if f.plant_id == plant.id])
                for fid, fruit in self.harvester.fruits.items():
                    if fruit.plant_id == plant.id:
                        self.harvester.update_fruit_development(
                            fid, fruit.days_since_fruit_set + self.dt_hours / 24.0,
                            self.farmer.environment.temperature_c)
                plant.fruit_count = len([f for f in self.harvester.fruits.values()
                                        if f.plant_id == plant.id and
                                        f.stage < FruitStage.OVER_RIPE])

    def _run_harvest(self):
        if self.cycle_count % 6 == 0:
            ready = self.harvester.find_harvestable_fruits()
            if ready:
                results = self.harvester.harvest_all_ready()
                self.stats["total_harvests"] += results["harvested"]
                self.stats["crop_yield_total_kg"] += results["total_weight_kg"]
                self._log_event("HARVEST",
                    f"Harvested {results['harvested']}/{results['total_ready']} fruits "
                    f"({results['total_weight_kg']:.2f}kg)")
                self.harvest_log.append({
                    "time_hours": self.simulation_time_hours,
                    "day": self.simulation_days,
                    "harvested_count": results["harvested"],
                    "weight_kg": results["total_weight_kg"],
                    "quality": results["quality_distribution"],
                })
            overripe = self.harvester.detect_overripe()
            if overripe:
                removed = self.harvester.clean_compost()
                if removed > 0:
                    self._log_event("COMPOST", f"Removed {removed} overripe/rotten fruits")

    def _update_plant_cycles(self):
        for plant in self.farmer.plants:
            if plant.health == HealthStatus.DEAD:
                continue
            if plant.growth_stage >= GrowthStage.FRUITING and plant.fruit_count > 0:
                for fid, fruit in self.harvester.fruits.items():
                    if fruit.plant_id == plant.id and fruit.stage >= FruitStage.TURNING:
                        break
                else:
                    continue
            self.farmer.update_plant_growth(plant, self.dt_hours)

    def run_cycle(self):
        self.simulation_time_hours += self.dt_hours
        self.simulation_days = int(self.simulation_time_hours / 24.0)
        self.cycle_count += 1

        self.farmer.run_cycle(self.dt_hours)
        self.farmer.water_plants()
        self.stats["total_water_used_ml"] += 50.0 * len(self.farmer.plants)

        self._run_plant_monitoring()
        self._run_disease_detection()
        self._run_pollination()
        self._update_fruit_development()
        self._update_plant_cycles()
        self._run_harvest()

        self._check_alerts()

    def get_status(self) -> Dict[str, Any]:
        farmer_status = self.farmer.get_status_report()
        pollination_stats = self.pollinator.get_statistics()
        harvest_stats = self.harvester.get_harvest_statistics()
        greenhouse_health = self.detector.get_greenhouse_health_summary()

        return {
            "simulation": {
                "time_hours": self.simulation_time_hours,
                "days": self.simulation_days,
                "cycles": self.cycle_count,
            },
            "greenhouse": farmer_status,
            "pollination": pollination_stats,
            "harvest": harvest_stats,
            "health": greenhouse_health,
            "stats": self.stats,
            "recent_alerts": list(self.alert_log)[-5:],
        }

    def print_status(self):
        status = self.get_status()
        print("\n" + "=" * 70)
        print(f"  SPACE GREENHOUSE STATUS - Day {status['simulation']['days']} "
              f"({status['simulation']['time_hours']:.1f} hours)")
        print("=" * 70)
        env = status["greenhouse"]["environment"]
        print(f"  Temperature: {env['temperature_c']:.1f}°C  |  "
              f"Humidity: {env['humidity_pct']:.1f}%  |  "
              f"CO2: {env['co2_ppm']:.0f} ppm")
        print(f"  Light: {env['light_lux']:.0f} lux  |  "
              f"Water Reservoir: {status['greenhouse']['water_system']['reservoir_ml']:.0f} ml")
        print("-" * 70)
        print(f"  Plants: {status['greenhouse']['total_plants']}  |  "
              f"Growth Stages: {status['greenhouse']['growth_stages']}")
        print(f"  Health: {status['greenhouse']['health_status']}")
        print("-" * 70)
        print(f"  Pollinations: {status['pollination']['total_pollinations']}  |  "
              f"Success Rate: {status['pollination']['success_rate']*100:.1f}%")
        print(f"  Harvests: {status['harvest']['total_harvested']}  |  "
              f"Total Weight: {status['harvest']['total_weight_kg']:.3f}kg")
        print(f"  Diseases Detected: {status['stats']['total_diseases_detected']}  |  "
              f"Emergencies: {status['stats']['emergency_events']}")
        if status["recent_alerts"]:
            print("-" * 70)
            print("  Recent Alerts:")
            for alert in status["recent_alerts"]:
                print(f"    [{alert['time_hours']:.1f}h] {alert['alert']}")
        print("=" * 70)

    def save_full_report(self, filepath: str):
        report = {
            "generated_at": datetime.now().isoformat(),
            "simulation_duration_hours": self.simulation_time_hours,
            "simulation_days": self.simulation_days,
            "status": self.get_status(),
            "event_log": list(self.event_log),
            "alert_log": list(self.alert_log),
            "harvest_log": list(self.harvest_log),
        }
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)


def main():
    print("=" * 70)
    print("  SPACE GREENHOUSE - NASA ISS Plant Habitat Simulator")
    print("  Zero-G Automated Farming System")
    print("=" * 70)
    print()

    sim = SpaceGreenhouseSimulator()
    total_days = 90

    print(f"Starting {total_days}-day simulation...")
    print(f"Plants: {len(sim.farmer.plants)}")
    print(f"Species: {set(p.species.name for p in sim.farmer.plants)}")
    print()

    start_time = time.time()

    for day in range(1, total_days + 1):
        for hour in range(24):
            sim.run_cycle()

        if day % 5 == 0 or day == 1:
            sim.print_status()

        if day % 15 == 0:
            sim.farmer.save_state(f"greenhouse_state_day_{day}.json")

    elapsed = time.time() - start_time

    print()
    print("=" * 70)
    print("  SIMULATION COMPLETE")
    print(f"  Simulated {total_days} days in {elapsed:.2f} seconds")
    print("=" * 70)

    final_status = sim.get_status()
    print(f"\n  Final Statistics:")
    print(f"    Total Harvests: {final_status['stats']['total_harvests']}")
    print(f"    Total Yield: {final_status['stats']['crop_yield_total_kg']:.3f} kg")
    print(f"    Total Water Used: {final_status['stats']['total_water_used_ml']:.0f} ml")
    print(f"    Total Pollinations: {final_status['stats']['total_pollinations']}")
    print(f"    Diseases Detected: {final_status['stats']['total_diseases_detected']}")
    print(f"    Emergency Events: {final_status['stats']['emergency_events']}")

    sim.save_full_report("final_mission_report.json")
    print(f"\n  Full report saved to: final_mission_report.json")


if __name__ == "__main__":
    main()