#!/usr/bin/env python3
"""
SpaceGreenhouse - 3D Visualization
Interactive 3D greenhouse render with Plotly
NASA ISS Plant Habitat - Mission Control View
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime


class GreenhouseVisualizer:
    def __init__(self, greenhouse_width: float = 200.0,
                 greenhouse_depth: float = 200.0,
                 greenhouse_height: float = 100.0):
        self.width = greenhouse_width
        self.depth = greenhouse_depth
        self.height = greenhouse_height
        self.fig = None

    def _create_greenhouse_mesh(self) -> Tuple[List, List, List]:
        x = [0, self.width, self.width, 0, 0,
             0, self.width, self.width, 0, 0]
        y = [0, 0, self.depth, self.depth, 0,
             0, 0, self.depth, self.depth, 0]
        z = [0, 0, 0, 0, 0,
             self.height, self.height, self.height, self.height, self.height]
        return x, y, z

    def create_greenhouse_scene(self, plants_data: List[Dict],
                                fruits_data: List[Dict] = None,
                                robot_position: Tuple[float, float, float] = None,
                                view_angle: str = "top") -> go.Figure:
        fig = go.Figure()

        fig.add_trace(go.Scatter3d(
            x=[0, self.width, self.width, 0, 0],
            y=[0, 0, self.depth, self.depth, 0],
            z=[0, 0, 0, 0, 0],
            mode='lines',
            line=dict(color='#00ff88', width=3, dash='solid'),
            name='Greenhouse Floor',
            showlegend=True
        ))

        fig.add_trace(go.Scatter3d(
            x=[0, self.width, self.width, 0, 0],
            y=[0, 0, self.depth, self.depth, 0],
            z=[self.height, self.height, self.height, self.height, self.height],
            mode='lines',
            line=dict(color='#00ff88', width=3, dash='solid'),
            name='Greenhouse Ceiling',
            showlegend=True
        ))

        for i in range(0, int(self.width) + 1, 50):
            fig.add_trace(go.Scatter3d(
                x=[i, i], y=[0, self.depth], z=[0, 0],
                mode='lines',
                line=dict(color='#00ff88', width=0.5, dash='dot'),
                showlegend=False
            ))
            fig.add_trace(go.Scatter3d(
                x=[i, i], y=[0, self.depth], z=[self.height, self.height],
                mode='lines',
                line=dict(color='#00ff88', width=0.5, dash='dot'),
                showlegend=False
            ))

        for j in range(0, int(self.depth) + 1, 50):
            fig.add_trace(go.Scatter3d(
                x=[0, self.width], y=[j, j], z=[0, 0],
                mode='lines',
                line=dict(color='#00ff88', width=0.5, dash='dot'),
                showlegend=False
            ))

        if plants_data:
            plant_x, plant_y, plant_z = [], [], []
            plant_colors, plant_sizes, plant_labels = [], [], []
            health_color_map = {
                "EXCELLENT": "#00ff00",
                "GOOD": "#88ff00",
                "FAIR": "#ffff00",
                "STRESSED": "#ff8800",
                "DISEASED": "#ff4444",
                "CRITICAL": "#ff0000",
                "DEAD": "#666666",
            }
            for plant in plants_data:
                plant_x.append(plant["position"][0])
                plant_y.append(plant["position"][1])
                plant_z.append(plant["height_cm"] / 2.0)
                plant_colors.append(health_color_map.get(plant.get("health", "GOOD"), "#ffffff"))
                plant_sizes.append(max(5, plant.get("leaf_area_cm2", 10) / 5.0))
                plant_labels.append(
                    f"Plant {plant['id']}<br>"
                    f"Species: {plant.get('species', 'Unknown')}<br>"
                    f"Stage: {plant.get('growth_stage', 'Unknown')}<br>"
                    f"Health: {plant.get('health', 'Unknown')}<br>"
                    f"Height: {plant['height_cm']:.1f}cm<br>"
                    f"Biomass: {plant.get('biomass_g', 0):.1f}g"
                )
            fig.add_trace(go.Scatter3d(
                x=plant_x, y=plant_y, z=plant_z,
                mode='markers',
                marker=dict(
                    size=plant_sizes,
                    color=plant_colors,
                    opacity=0.8,
                    symbol='circle',
                    line=dict(color='white', width=1)
                ),
                text=plant_labels,
                hoverinfo='text',
                name='Plants',
                showlegend=True
            ))

        if fruits_data:
            fruit_x, fruit_y, fruit_z = [], [], []
            fruit_colors, fruit_sizes = [], []
            for fruit in fruits_data:
                if fruit.get("stage", "RED_RIPE") != "ROTTEN":
                    fruit_x.append(fruit["position"][0])
                    fruit_y.append(fruit["position"][1])
                    fruit_z.append(fruit["position"][2])
                    rgb = fruit.get("color_rgb", (1.0, 0.0, 0.0))
                    fruit_colors.append(f'rgb({int(rgb[0]*255)},{int(rgb[1]*255)},{int(rgb[2]*255)})')
                    fruit_sizes.append(max(3, fruit.get("diameter_cm", 2) * 2))
            if fruit_x:
                fig.add_trace(go.Scatter3d(
                    x=fruit_x, y=fruit_y, z=fruit_z,
                    mode='markers',
                    marker=dict(
                        size=fruit_sizes,
                        color=fruit_colors,
                        opacity=0.9,
                        symbol='diamond',
                        line=dict(color='white', width=0.5)
                    ),
                    name='Fruits',
                    showlegend=True
                ))

        if robot_position:
            fig.add_trace(go.Scatter3d(
                x=[robot_position[0]],
                y=[robot_position[1]],
                z=[robot_position[2]],
                mode='markers',
                marker=dict(
                    size=12,
                    color='#00ffff',
                    symbol='cross',
                    line=dict(color='white', width=2)
                ),
                name='Robot Arm',
                showlegend=True
            ))

        camera = dict()
        if view_angle == "top":
            camera = dict(eye=dict(x=self.width/2, y=self.depth/2, z=self.height*2))
        elif view_angle == "front":
            camera = dict(eye=dict(x=self.width/2, y=-self.depth, z=self.height/2))
        elif view_angle == "side":
            camera = dict(eye=dict(x=-self.width, y=self.depth/2, z=self.height/2))
        elif view_angle == "corner":
            camera = dict(eye=dict(x=self.width*1.5, y=self.depth*1.5, z=self.height*1.5))

        fig.update_layout(
            title=dict(
                text="Space Greenhouse - 3D Mission Control View",
                font=dict(size=20, color='#00ff88', family='monospace'),
                x=0.5
            ),
            scene=dict(
                xaxis=dict(title='X (cm)', range=[-10, self.width+10],
                          gridcolor='#1a3a2a', showbackground=True,
                          backgroundcolor='#0a1a0a'),
                yaxis=dict(title='Y (cm)', range=[-10, self.depth+10],
                          gridcolor='#1a3a2a', showbackground=True,
                          backgroundcolor='#0a1a0a'),
                zaxis=dict(title='Z (cm)', range=[0, self.height+20],
                          gridcolor='#1a3a2a', showbackground=True,
                          backgroundcolor='#0a1a0a'),
                camera=camera,
                aspectmode='data'
            ),
            paper_bgcolor='#0a0a0a',
            plot_bgcolor='#0a0a0a',
            font=dict(color='#00ff88', family='monospace'),
            showlegend=True,
            legend=dict(
                x=0.01, y=0.99,
                bgcolor='rgba(10,10,10,0.8)',
                bordercolor='#00ff88'
            )
        )

        self.fig = fig
        return fig

    def create_dashboard(self, status_data: Dict) -> go.Figure:
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "Plant Growth Over Time",
                "Health Distribution",
                "Water Usage (ml/day)",
                "Harvest Yield (kg)",
                "Temperature & Humidity",
                "Disease Detection History"
            ),
            specs=[
                [{"type": "scatter"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "scatter"}],
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.10
        )

        days = list(range(1, status_data.get("simulation", {}).get("days", 90) + 1))
        growth_data = np.random.normal(0.15, 0.05, len(days)).cumsum() * 30
        fig.add_trace(
            go.Scatter(x=days, y=growth_data, mode='lines',
                      line=dict(color='#00ff88', width=2),
                      fill='tozeroy', fillcolor='rgba(0,255,136,0.1)',
                      name='Avg Height (cm)'),
            row=1, col=1
        )

        health_data = status_data.get("greenhouse", {}).get("health_status", {})
        if health_data:
            fig.add_trace(
                go.Pie(labels=list(health_data.keys()),
                      values=list(health_data.values()),
                      hole=0.4,
                      marker=dict(colors=['#00ff00', '#88ff00', '#ffff00',
                                         '#ff8800', '#ff4444', '#ff0000', '#666666']),
                      name='Health'),
                row=1, col=2
            )

        water_data = np.random.normal(500, 50, len(days))
        fig.add_trace(
            go.Bar(x=days, y=water_data, marker_color='#0088ff',
                  name='Water (ml)'),
            row=2, col=1
        )

        harvest_data = np.zeros(len(days))
        for h in status_data.get("harvest_log", []):
            day_idx = int(h.get("day", 1)) - 1
            if 0 <= day_idx < len(days):
                harvest_data[day_idx] += h.get("weight_kg", 0)
        fig.add_trace(
            go.Bar(x=days, y=harvest_data, marker_color='#ff8800',
                  name='Harvest (kg)'),
            row=2, col=2
        )

        env = status_data.get("greenhouse", {}).get("environment", {})
        temp_data = np.random.normal(float(env.get("temperature_c", 22)), 1, len(days))
        hum_data = np.random.normal(float(env.get("humidity_pct", 60)), 3, len(days))
        fig.add_trace(
            go.Scatter(x=days, y=temp_data, mode='lines',
                      line=dict(color='#ff4444', width=2), name='Temp (°C)'),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=days, y=hum_data, mode='lines',
                      line=dict(color='#4488ff', width=2), name='Humidity (%)'),
            row=3, col=1
        )

        disease_counts = [status_data.get("stats", {}).get("total_diseases_detected", 0)]
        disease_days = [1]
        fig.add_trace(
            go.Scatter(x=disease_days, y=disease_counts, mode='markers+lines',
                      line=dict(color='#ff0000', width=2),
                      marker=dict(size=10, symbol='x'),
                      name='Diseases'),
            row=3, col=2
        )

        fig.update_layout(
            title=dict(
                text="Space Greenhouse - Mission Dashboard",
                font=dict(size=22, color='#00ff88', family='monospace'),
                x=0.5
            ),
            paper_bgcolor='#0a0a0a',
            plot_bgcolor='#0a0a0a',
            font=dict(color='#00ff88', family='monospace'),
            showlegend=True,
            height=1000,
            legend=dict(
                bgcolor='rgba(10,10,10,0.8)',
                bordercolor='#00ff88'
            )
        )

        return fig

    def create_growth_animation(self, all_plant_data: List[List[Dict]],
                                interval_ms: int = 200) -> go.Figure:
        fig = self.create_greenhouse_scene(all_plant_data[0] if all_plant_data else [])

        frames = []
        for day_data in all_plant_data:
            plant_x, plant_y, plant_z = [], [], []
            plant_colors, plant_sizes = [], []
            health_color_map = {
                "EXCELLENT": "#00ff00", "GOOD": "#88ff00", "FAIR": "#ffff00",
                "STRESSED": "#ff8800", "DISEASED": "#ff4444",
                "CRITICAL": "#ff0000", "DEAD": "#666666",
            }
            for plant in day_data:
                plant_x.append(plant["position"][0])
                plant_y.append(plant["position"][1])
                plant_z.append(plant.get("height_cm", 0) / 2.0)
                plant_colors.append(health_color_map.get(plant.get("health", "GOOD"), "#ffffff"))
                plant_sizes.append(max(5, plant.get("leaf_area_cm2", 10) / 5.0))

            frame = go.Frame(
                data=[go.Scatter3d(
                    x=plant_x, y=plant_y, z=plant_z,
                    mode='markers',
                    marker=dict(size=plant_sizes, color=plant_colors, opacity=0.8)
                )],
                name=f"day_{day_data[0].get('age_days', 0):.0f}"
            )
            frames.append(frame)

        fig.frames = frames

        fig.update_layout(
            updatemenus=[{
                "type": "buttons",
                "buttons": [
                    {"label": "▶ Play", "method": "animate",
                     "args": [None, {"frame": {"duration": interval_ms, "redraw": True},
                                    "fromcurrent": True}]},
                    {"label": "⏸ Pause", "method": "animate",
                     "args": [[None], {"frame": {"duration": 0, "redraw": False},
                                      "mode": "immediate"}]},
                ],
                "x": 0.1, "y": 0.02,
                "bgcolor": "#0a1a0a",
                "bordercolor": "#00ff88"
            }]
        )

        return fig

    def save_html(self, filepath: str = "greenhouse_3d.html"):
        if self.fig:
            self.fig.write_html(filepath)
            print(f"[Visualizer] 3D greenhouse saved to {filepath}")

    def save_image(self, filepath: str = "greenhouse_3d.png"):
        if self.fig:
            self.fig.write_image(filepath, width=1920, height=1080, scale=2)
            print(f"[Visualizer] Image saved to {filepath}")


def demo_visualization():
    print("=" * 60)
    print("  SpaceGreenhouse - 3D Visualization Demo")
    print("=" * 60)

    visualizer = GreenhouseVisualizer(200, 200, 100)

    sample_plants = []
    for i in range(24):
        row = i // 6
        col = i % 6
        plant = {
            "id": i,
            "position": (20 + col * 30, 20 + row * 30),
            "species": ["LETTUCE", "TOMATO", "PEPPER", "WHEAT", "BASIL", "STRAWBERRY"][i % 6],
            "growth_stage": "VEGETATIVE" if i % 4 < 2 else "FRUITING",
            "health": ["EXCELLENT", "GOOD", "FAIR", "STRESSED", "DISEASED", "GOOD"][i % 6],
            "height_cm": np.random.uniform(10, 40),
            "leaf_area_cm2": np.random.uniform(20, 200),
            "biomass_g": np.random.uniform(10, 80),
            "age_days": np.random.uniform(10, 60),
            "fruit_count": np.random.randint(0, 8) if i % 4 >= 2 else 0,
        }
        sample_plants.append(plant)

    sample_fruits = []
    for i in range(10):
        fruit = {
            "fruit_id": i,
            "plant_id": i % 24,
            "position": (
                20 + (i % 6) * 30 + np.random.uniform(-8, 8),
                20 + (i // 6) * 30 + np.random.uniform(-8, 8),
                np.random.uniform(15, 35)
            ),
            "stage": "RED_RIPE" if i < 7 else "TURNING",
            "diameter_cm": np.random.uniform(1.5, 5.0),
            "color_rgb": (1.0, 0.0, 0.0) if i < 7 else (0.8, 0.3, 0.0),
        }
        sample_fruits.append(fruit)

    fig = visualizer.create_greenhouse_scene(
        sample_plants,
        sample_fruits,
        robot_position=(100, 100, 50),
        view_angle="corner"
    )

    fig.show()
    visualizer.save_html("greenhouse_3d.html")

    sample_status = {
        "simulation": {"days": 45, "time_hours": 1080.0},
        "greenhouse": {
            "health_status": {"GOOD": 12, "FAIR": 6, "STRESSED": 3, "DISEASED": 2, "EXCELLENT": 1},
            "environment": {"temperature_c": 22.5, "humidity_pct": 62.0}
        },
        "harvest_log": [
            {"day": 15, "weight_kg": 0.5}, {"day": 20, "weight_kg": 1.2},
            {"day": 25, "weight_kg": 2.1}, {"day": 30, "weight_kg": 3.5},
            {"day": 35, "weight_kg": 4.8}, {"day": 40, "weight_kg": 6.2},
        ],
        "stats": {"total_diseases_detected": 5},
    }

    dashboard = visualizer.create_dashboard(sample_status)
    dashboard.show()
    dashboard.write_html("greenhouse_dashboard.html")

    print("\n[Visualizer] Demo complete. Files saved:")
    print("  - greenhouse_3d.html")
    print("  - greenhouse_dashboard.html")


if __name__ == "__main__":
    demo_visualization()