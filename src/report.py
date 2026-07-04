"""
report.py - Text summaries and a trend chart for a PlantMonitor's history.
"""
import matplotlib.pyplot as plt

from plant import PlantMonitor


def generate_text_report(monitor: PlantMonitor) -> str:
    lines = [f"=== Health report: {monitor.name} ===", ""]

    if not monitor.history:
        lines.append("No readings recorded yet.")
        return "\n".join(lines)

    latest = monitor.latest()
    lines.append(f"Readings recorded: {len(monitor.history)}")
    lines.append(f"Latest reading ({latest.source or 'unnamed'}):")
    lines.append(f"  Health score : {latest.metrics.health_score:.1f} / 100")
    lines.append(f"  Green tissue : {latest.metrics.green_pct:.1f}%")
    lines.append(f"  Yellow tissue: {latest.metrics.yellow_pct:.1f}%")
    lines.append(f"  Brown tissue : {latest.metrics.brown_pct:.1f}%")
    lines.append("")

    if monitor.alerts:
        lines.append(f"Alerts ({len(monitor.alerts)}):")
        for alert in monitor.alerts[-10:]:
            lines.append(f"  [{alert.severity.upper()}] {alert.timestamp:%Y-%m-%d %H:%M} - {alert.message}")
    else:
        lines.append("Alerts: none")

    return "\n".join(lines)


def plot_health_trend(monitor: PlantMonitor, out_path: str) -> None:
    scores = monitor.trend()
    if not scores:
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(1, len(scores) + 1), scores, marker="o", color="#2e7d32")
    ax.axhline(monitor.warning_score, color="orange", linestyle="--", label="warning threshold")
    ax.axhline(monitor.critical_score, color="red", linestyle="--", label="critical threshold")
    ax.set_xlabel("Reading #")
    ax.set_ylabel("Health score (0-100)")
    ax.set_title(f"Health trend: {monitor.name}")
    ax.set_ylim(0, 100)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
