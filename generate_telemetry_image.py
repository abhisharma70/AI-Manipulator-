#!/usr/bin/env python3
"""Render a compact image summary from one simulation_run.log."""

import argparse
import re
import statistics
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
POSITION_RE = re.compile(
    r"Target Detected at base_link:\s*X=([-+0-9.eE]+),\s*Y=([-+0-9.eE]+),\s*Z=([-+0-9.eE]+)"
)
STATE_RE = re.compile(r"\[STATE\s+(\d+)/7\]\s*([^\r\n]+)")
CONTROLLER_RE = re.compile(r"Configured and activated (joint_state_broadcaster|arm_controller|gripper_controller)")

WIDTH = 1280
HEIGHT = 820
BACKGROUND = (25, 29, 38)
PANEL = (37, 43, 55)
GRID = (65, 73, 87)
TEXT = (235, 239, 244)
MUTED = (155, 166, 180)
RED = (86, 102, 240)
CYAN = (226, 190, 65)
GREEN = (105, 205, 125)
AMBER = (65, 174, 245)


def draw_text(image, text, point, scale=0.55, color=TEXT, thickness=1):
    cv2.putText(image, str(text), point, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def median_position(samples):
    window = samples[:10] if len(samples) < 20 else samples[:20]
    return tuple(statistics.median(sample[axis] for sample in window) for axis in range(3))


def parse_log(log_path):
    content = ANSI_RE.sub("", log_path.read_text(encoding="utf-8", errors="replace"))
    positions = [tuple(float(value) for value in match) for match in POSITION_RE.findall(content)]
    states = {}
    for number, name in STATE_RE.findall(content):
        states[int(number)] = name.strip()
    controllers = set(CONTROLLER_RE.findall(content))
    crashed = "ODE INTERNAL ERROR" in content or "Aborted (Signal" in content
    completed = "Pick-and-Place Cycle successfully completed!" in content
    return positions, states, controllers, crashed, completed


def draw_card(image, x, label, value, detail, accent):
    cv2.rectangle(image, (x, 126), (x + 364, 236), PANEL, -1, cv2.LINE_AA)
    cv2.rectangle(image, (x, 126), (x + 5, 236), accent, -1)
    draw_text(image, label.upper(), (x + 22, 155), 0.42, MUTED)
    draw_text(image, value, (x + 22, 199), 1.05, TEXT, 2)
    draw_text(image, detail, (x + 22, 222), 0.38, MUTED)


def draw_telemetry_chart(image, positions):
    chart_x = 170
    chart_width = 1038
    row_top = 365
    row_height = 78
    axes = ((0, "X (m)", RED), (1, "Y (m)", CYAN), (2, "Z (m)", GREEN))

    if not positions:
        cv2.rectangle(image, (52, 342), (1228, 632), PANEL, -1, cv2.LINE_AA)
        draw_text(image, "No target-position samples found in this run log.", (84, 400), 0.7, MUTED)
        return

    for axis, label, color in axes:
        top = row_top + axis * (row_height + 12)
        values = np.asarray([sample[axis] for sample in positions], dtype=np.float64)
        low = float(values.min())
        high = float(values.max())
        padding = max((high - low) * 0.12, 0.005)
        low -= padding
        high += padding

        draw_text(image, label, (58, top + 36), 0.52, color, 2)
        for fraction in (0.0, 0.5, 1.0):
            y = int(top + fraction * row_height)
            cv2.line(image, (chart_x, y), (chart_x + chart_width, y), GRID, 1, cv2.LINE_AA)
        draw_text(image, f"{high:.3f}", (112, top + 11), 0.34, MUTED)
        draw_text(image, f"{low:.3f}", (112, top + row_height), 0.34, MUTED)

        sample_count = len(values)
        points = []
        for index, value in enumerate(values):
            x = chart_x + round(index * chart_width / max(sample_count - 1, 1))
            y = top + row_height - round((value - low) * row_height / (high - low))
            points.append((x, y))
        if len(points) > 1:
            cv2.polylines(image, [np.asarray(points, dtype=np.int32)], False, color, 2, cv2.LINE_AA)
        cv2.circle(image, points[0], 4, TEXT, -1, cv2.LINE_AA)
        cv2.circle(image, points[-1], 5, color, -1, cv2.LINE_AA)

    draw_text(image, "DETECTED TARGET POSITION BY SAMPLE", (58, 337), 0.42, MUTED)
    draw_text(image, "first", (chart_x, 667), 0.36, MUTED)
    draw_text(image, "latest", (chart_x + chart_width - 44, 667), 0.36, MUTED)


def generate(log_path, output_path):
    positions, states, controllers, crashed, completed = parse_log(log_path)
    image = np.full((HEIGHT, WIDTH, 3), BACKGROUND, dtype=np.uint8)
    cv2.rectangle(image, (0, 0), (WIDTH, 8), RED, -1)

    run_time = datetime.fromtimestamp(log_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    draw_text(image, "ROBOTICS / SIMULATION REPORT", (58, 48), 0.42, CYAN, 1)
    draw_text(image, "Pick-and-place telemetry", (58, 91), 1.05, TEXT, 2)
    draw_text(image, f"Run log updated {run_time}", (850, 76), 0.46, MUTED)

    if crashed:
        result, result_color = "GAZEBO ABORT", RED
    elif completed:
        result, result_color = "CYCLE COMPLETE", GREEN
    elif states:
        result, result_color = "RUN INCOMPLETE", AMBER
    else:
        result, result_color = "NO RUN DATA", MUTED
    cv2.rectangle(image, (1010, 94), (1220, 119), PANEL, -1, cv2.LINE_AA)
    draw_text(image, result, (1022, 112), 0.42, result_color, 1)

    if len(positions) >= 2:
        first = median_position(positions[:20])
        last = median_position(positions[-20:])
        displacement = float(np.linalg.norm(np.asarray(last) - np.asarray(first)))
        movement_value = f"{displacement * 100:.1f} cm"
        movement_detail = "observed first-to-last target shift"
    elif positions:
        first = last = median_position(positions)
        movement_value = "N/A"
        movement_detail = "only one target sample"
    else:
        first = last = None
        movement_value = "N/A"
        movement_detail = "no target samples found"

    draw_card(image, 58, "Target samples", str(len(positions)), "from object detector log messages", CYAN)
    draw_card(image, 458, "Sequence progress", f"{len(states)} / 7", "orchestrator stages observed", GREEN)
    draw_card(image, 858, "Target displacement", movement_value, movement_detail, AMBER)

    draw_text(image, "SEQUENCE", (58, 278), 0.42, MUTED)
    for index in range(1, 8):
        x = 58 + (index - 1) * 166
        reached = index in states
        color = GREEN if completed and reached else (CYAN if reached else PANEL)
        cv2.rectangle(image, (x, 291), (x + 156, 324), color, -1, cv2.LINE_AA)
        label = states.get(index, f"Stage {index}")
        if len(label) > 21:
            label = label[:18] + "..."
        draw_text(image, f"{index}. {label}", (x + 8, 313), 0.34, BACKGROUND if reached else MUTED)

    draw_telemetry_chart(image, positions)

    if first is not None and last is not None:
        draw_text(image, "EARLIEST", (58, 723), 0.38, MUTED)
        draw_text(image, "X %.3f   Y %.3f   Z %.3f m" % first, (58, 750), 0.52, TEXT)
        draw_text(image, "LATEST", (680, 723), 0.38, MUTED)
        draw_text(image, "X %.3f   Y %.3f   Z %.3f m" % last, (680, 750), 0.52, TEXT)

    controller_status = f"Controllers active: {len(controllers)}/3"
    draw_text(image, controller_status, (58, 796), 0.42, MUTED)
    draw_text(image, "Generated from simulation_run.log", (880, 796), 0.42, MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), image):
        raise OSError(f"Could not write telemetry image to {output_path}")
    print(f"Telemetry image written to {output_path}")


def main():
    project_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=project_dir / "simulation_run.log")
    parser.add_argument("--output", type=Path, default=project_dir / "simulation_telemetry.png")
    args = parser.parse_args()

    if not args.log.is_file():
        parser.error(f"run log does not exist: {args.log}")
    generate(args.log, args.output)


if __name__ == "__main__":
    main()
