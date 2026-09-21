
"""Terminal progress display with speed and ETA."""

from __future__ import annotations
import shutil
import sys
import time


class ProgressBar:
    def __init__(self, total: int, label: str = "Processing", width: int = 34):
        self.total = max(total, 1)
        self.label = label
        self.width = width
        self.start = time.monotonic()

    def update(self, current: int, detail: str = "") -> None:
        elapsed = max(time.monotonic() - self.start, 0.001)
        rate = current / elapsed
        remaining = max(self.total - current, 0)
        eta = remaining / rate if rate > 0 else 0

        fraction = min(max(current / self.total, 0), 1)
        filled = int(self.width * fraction)
        bar = "█" * filled + "░" * (self.width - filled)

        percent = fraction * 100
        eta_text = self._format_time(eta)
        elapsed_text = self._format_time(elapsed)

        line = (
            f"\r{self.label:<15} [{bar}] {percent:6.2f}% "
            f"{current:,}/{self.total:,}  "
            f"ETA {eta_text}  Elapsed {elapsed_text}"
        )

        if detail:
            line += f"  {detail[:32]}"

        # Clamp to terminal width so the line never wraps (wrapping breaks \r).
        cols = shutil.get_terminal_size(fallback=(120, 24)).columns
        line = line[: cols - 1]

        sys.stdout.write(line)
        sys.stdout.flush()

        if current >= self.total:
            sys.stdout.write("\n")

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds}s"
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes}m {secs:02d}s"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes:02d}m"
