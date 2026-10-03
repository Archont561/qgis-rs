#!/usr/bin/env python3
"""Headless PyQt screenshot/analyse/improve loop for one custom-painted widget.

This is a small proof of concept, not a QGIS plugin runtime. It deliberately keeps
three seams replaceable:

* ``DemoWidget`` renders a real Qt widget and captures it with ``grab()``.
* ``analyze_image`` extracts deterministic metrics from the captured ``QImage``.
* ``HeuristicReviewer`` can be replaced with ``--reviewer-command`` so an agent or
  vision model can inspect the PNG and return the next JSON design specification.

The QGIS adaptation point is ``load_qt()``: when executed inside QGIS it prefers
``qgis.PyQt``; otherwise it uses an installed PyQt/PySide binding.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence


# Keep imports lazy. This lets the pure design and reviewer tests run without Qt.
def load_qt() -> tuple[Any, Any, Any, str]:
    """Return ``(QtCore, QtGui, QtWidgets, binding)`` for QGIS or standalone Qt."""

    attempts: list[tuple[str, Any]] = [
        ("qgis.PyQt", lambda: __import__("qgis.PyQt", fromlist=["QtCore", "QtGui", "QtWidgets"])),
        ("PyQt5", lambda: __import__("PyQt5", fromlist=["QtCore", "QtGui", "QtWidgets"])),
        ("PyQt6", lambda: __import__("PyQt6", fromlist=["QtCore", "QtGui", "QtWidgets"])),
        ("PySide6", lambda: __import__("PySide6", fromlist=["QtCore", "QtGui", "QtWidgets"])),
    ]
    errors: list[str] = []
    for name, importer in attempts:
        try:
            package = importer()
            return package.QtCore, package.QtGui, package.QtWidgets, name
        except Exception as exc:  # bindings fail differently when optional modules are absent
            errors.append(f"{name}: {exc}")
    message = "No usable Qt binding found. Tried: " + "; ".join(errors)
    raise RuntimeError(message)


@dataclass(frozen=True)
class DesignSpec:
    """Serializable visual parameters for the single demo widget."""

    width: int = 520
    height: int = 300
    background: str = "#d7d7d7"
    surface: str = "#eeeeee"
    accent: str = "#b8b8b8"
    text: str = "#929292"
    muted: str = "#aaaaaa"
    margin: int = 12
    radius: int = 2
    title_size: int = 18
    title: str = "QGIS UI design loop"
    subtitle: str = "One widget, one screenshot, one improvement"
    button: str = "Continue"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DesignSpec":
        fields = {field_name for field_name in cls.__dataclass_fields__}
        unknown = sorted(set(value) - fields)
        if unknown:
            raise ValueError(f"Unknown design fields: {', '.join(unknown)}")
        current = asdict(cls())
        current.update(value)
        return cls(**current)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DesignAnalysis:
    iteration: int
    screenshot: str
    width: int
    height: int
    background_rgb: tuple[int, int, int]
    mean_luma: float
    luma_stddev: float
    non_background_ratio: float
    text_contrast: float
    muted_contrast: float
    accent_contrast: float
    white_on_accent_contrast: float
    score: float
    issues: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        result = asdict(self)
        result["background_rgb"] = list(self.background_rgb)
        result["issues"] = list(self.issues)
        return result


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected six-digit colour, got {value!r}")
    try:
        return tuple(
            int(value[index : index + 2], 16) for index in (0, 2, 4)
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Invalid colour: #{value}") from exc


def relative_luminance(rgb: Sequence[int]) -> float:
    channels = []
    for channel in rgb:
        value = channel / 255.0
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: Sequence[int], second: Sequence[int]) -> float:
    light = max(relative_luminance(first), relative_luminance(second))
    dark = min(relative_luminance(first), relative_luminance(second))
    return (light + 0.05) / (dark + 0.05)


def _bounded_score(value: float, target: float) -> float:
    return min(1.0, value / target)


def spec_quality(spec: DesignSpec) -> float:
    """Score only independently knowable design constraints, from 0.0 to 1.0."""

    surface = hex_rgb(spec.surface)
    text = hex_rgb(spec.text)
    muted = hex_rgb(spec.muted)
    accent = hex_rgb(spec.accent)
    checks = [
        _bounded_score(contrast_ratio(text, surface), 7.0),
        _bounded_score(contrast_ratio(muted, surface), 4.5),
        _bounded_score(contrast_ratio(accent, surface), 3.0),
        _bounded_score(contrast_ratio((255, 255, 255), accent), 4.5),
        min(1.0, max(0.0, spec.margin / 32.0)),
        1.0 if 12 <= spec.radius <= 28 else 0.65,
        1.0 if 24 <= spec.title_size <= 36 else 0.7,
        1.0 if spec.width >= 640 and spec.height >= 360 else 0.7,
    ]
    return round(sum(checks) / len(checks), 4)


def analyze_image(image: Any, spec: DesignSpec, iteration: int, screenshot: Path) -> DesignAnalysis:
    """Analyze a captured Qt image without PIL/OpenCV or a display server."""

    width, height = image.width(), image.height()
    step = max(1, min(width, height) // 80)
    samples: list[float] = []
    background = image.pixelColor(0, 0)
    background_rgb = (background.red(), background.green(), background.blue())
    different = 0
    sample_count = 0
    for y in range(0, height, step):
        for x in range(0, width, step):
            color = image.pixelColor(x, y)
            rgb = (color.red(), color.green(), color.blue())
            samples.append(relative_luminance(rgb))
            if sum(abs(rgb[index] - background_rgb[index]) for index in range(3)) > 30:
                different += 1
            sample_count += 1
    mean = sum(samples) / len(samples) if samples else 0.0
    variance = sum((value - mean) ** 2 for value in samples) / len(samples) if samples else 0.0
    surface = hex_rgb(spec.surface)
    text = hex_rgb(spec.text)
    muted = hex_rgb(spec.muted)
    accent = hex_rgb(spec.accent)
    text_contrast = contrast_ratio(text, surface)
    muted_contrast = contrast_ratio(muted, surface)
    accent_contrast = contrast_ratio(accent, surface)
    white_on_accent = contrast_ratio((255, 255, 255), accent)
    issues: list[str] = []
    if text_contrast < 4.5:
        issues.append("text contrast below WCAG AA body-text target")
    if muted_contrast < 3.0:
        issues.append("muted text is too faint")
    if white_on_accent < 4.5:
        issues.append("button text contrast below target")
    if spec.margin < 24:
        issues.append("content margin is cramped")
    if spec.title_size < 24:
        issues.append("title hierarchy is weak")
    if spec.width < 640 or spec.height < 360:
        issues.append("preview canvas is small")
    return DesignAnalysis(
        iteration=iteration,
        screenshot=str(screenshot),
        width=width,
        height=height,
        background_rgb=background_rgb,
        mean_luma=round(mean, 5),
        luma_stddev=round(variance**0.5, 5),
        non_background_ratio=round(different / sample_count, 5) if sample_count else 0.0,
        text_contrast=round(text_contrast, 3),
        muted_contrast=round(muted_contrast, 3),
        accent_contrast=round(accent_contrast, 3),
        white_on_accent_contrast=round(white_on_accent, 3),
        score=spec_quality(spec),
        issues=tuple(issues),
    )


class HeuristicReviewer:
    """Deterministic stand-in for an agent reviewer; useful for a smoke test."""

    def improve(self, spec: DesignSpec, analysis: DesignAnalysis) -> DesignSpec:
        changes: dict[str, Any] = {}
        if analysis.text_contrast < 4.5:
            changes["text"] = "#172033"
        if analysis.muted_contrast < 3.0:
            changes["muted"] = "#526077"
        if analysis.white_on_accent_contrast < 4.5 or analysis.accent_contrast < 2.5:
            changes["accent"] = "#1d4ed8"
        if spec.margin < 32:
            changes["margin"] = 32
        if spec.radius < 16:
            changes["radius"] = 20
        if spec.title_size < 28:
            changes["title_size"] = 28
        if spec.width < 720:
            changes["width"] = 720
        if spec.height < 420:
            changes["height"] = 420
        if spec.background.lower() == spec.surface.lower():
            changes["background"] = "#f3f6fb"
        elif spec.surface.lower() == "#eeeeee":
            changes["surface"] = "#ffffff"
        return replace(spec, **changes)


def improve_with_command(
    command: str, spec: DesignSpec, analysis: DesignAnalysis, screenshot: Path, iteration: int
) -> DesignSpec:
    """Ask an external agent/vision model for the next complete JSON design spec."""

    payload = {
        "iteration": iteration,
        "screenshot": str(screenshot.resolve()),
        "spec": spec.to_json(),
        "analysis": analysis.to_json(),
        "instruction": (
            "Return one complete DesignSpec JSON object. "
            "Preserve behavior and improve visual design only."
        ),
    }
    result = subprocess.run(
        shlex.split(command),
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"reviewer command failed ({result.returncode}): {result.stderr.strip()}"
        )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"reviewer command did not return JSON: {result.stdout[:500]!r}"
        ) from exc
    return DesignSpec.from_mapping(value)


def _qt_alignment(QtCore: Any) -> Any:
    qt = QtCore.Qt
    try:
        return qt.AlignCenter
    except AttributeError:
        return qt.AlignmentFlag.AlignCenter


def make_widget(QtCore: Any, QtGui: Any, QtWidgets: Any, spec: DesignSpec) -> Any:
    """Create one custom-painted QWidget; no child widgets or QGIS state."""

    class DemoWidget(QtWidgets.QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setFixedSize(spec.width, spec.height)
            self.setWindowTitle("QGIS UI design loop probe")
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)

        def paintEvent(self, _event: Any) -> None:  # noqa: N802 - Qt override
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.fillRect(self.rect(), QtGui.QColor(spec.background))
            card = self.rect().adjusted(spec.margin, spec.margin, -spec.margin, -spec.margin)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(spec.surface))
            painter.drawRoundedRect(card, spec.radius, spec.radius)

            center = card.center()
            title_rect = QtCore.QRect(card.left() + 24, center.y() - 70, card.width() - 48, 44)
            title_font = QtGui.QFont()
            title_font.setPointSize(spec.title_size)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QtGui.QColor(spec.text))
            painter.drawText(title_rect, _qt_alignment(QtCore), spec.title)

            subtitle_rect = QtCore.QRect(card.left() + 24, center.y() - 20, card.width() - 48, 28)
            subtitle_font = QtGui.QFont()
            subtitle_font.setPointSize(11)
            painter.setFont(subtitle_font)
            painter.setPen(QtGui.QColor(spec.muted))
            painter.drawText(subtitle_rect, _qt_alignment(QtCore), spec.subtitle)

            button = QtCore.QRect(center.x() - 72, center.y() + 34, 144, 42)
            painter.setBrush(QtGui.QColor(spec.accent))
            painter.drawRoundedRect(button, 12, 12)
            button_font = QtGui.QFont()
            button_font.setPointSize(11)
            button_font.setBold(True)
            painter.setFont(button_font)
            painter.setPen(QtGui.QColor("#ffffff"))
            painter.drawText(button, _qt_alignment(QtCore), spec.button)
            painter.end()

    return DemoWidget()


def run_loop(
    spec: DesignSpec, iterations: int, output: Path, reviewer_command: str | None
) -> list[DesignAnalysis]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QtCore, QtGui, QtWidgets, binding = load_qt()
    output.mkdir(parents=True, exist_ok=True)
    (output / "binding.txt").write_text(binding + "\n", encoding="utf-8")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    reviewer: Any = HeuristicReviewer()
    history: list[DesignAnalysis] = []
    current = spec
    for iteration in range(iterations):
        widget = make_widget(QtCore, QtGui, QtWidgets, current)
        widget.show()
        app.processEvents()
        screenshot = output / f"iteration-{iteration:02d}.png"
        pixmap = widget.grab()
        if not pixmap.save(str(screenshot), "PNG"):
            raise RuntimeError(f"could not save screenshot: {screenshot}")
        analysis = analyze_image(pixmap.toImage(), current, iteration, screenshot)
        (output / f"iteration-{iteration:02d}.json").write_text(
            json.dumps(
                {"spec": current.to_json(), "analysis": analysis.to_json()}, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        history.append(analysis)
        widget.close()
        if reviewer_command:
            current = improve_with_command(
                reviewer_command, current, analysis, screenshot, iteration
            )
        else:
            current = reviewer.improve(current, analysis)
        if current == spec and iteration > 0:
            break
        spec = current
    (output / "history.json").write_text(
        json.dumps([analysis.to_json() for analysis in history], indent=2) + "\n", encoding="utf-8"
    )
    (output / "final-spec.json").write_text(
        json.dumps(current.to_json(), indent=2) + "\n", encoding="utf-8"
    )
    app.quit()
    return history


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--reviewer-command",
        help=(
            "command that reads the iteration JSON payload on stdin and returns "
            "a complete DesignSpec JSON object"
        ),
    )
    args = parser.parse_args(argv)
    try:
        history = run_loop(
            DesignSpec(), max(1, args.iterations), args.output, args.reviewer_command
        )
    except Exception as exc:
        print(f"design-loop: {exc}", file=sys.stderr)
        return 2
    for analysis in history:
        print(
            f"iteration={analysis.iteration} screenshot={analysis.screenshot} "
            f"score={analysis.score:.4f} issues={'; '.join(analysis.issues) or 'none'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
