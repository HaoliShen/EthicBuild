from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_MANUAL_PATH = Path(__file__).resolve().parent.parent / "data" / "ethics_manual.yaml"


@dataclass
class ValueManual:
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MANUAL_PATH) -> "ValueManual":
        manual_path = Path(path)
        with manual_path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file)
        return cls(raw=raw)

    @property
    def values(self) -> dict[str, Any]:
        return self.raw.get("values", {})

    @property
    def taxonomy(self) -> dict[str, Any]:
        return self.raw.get("taxonomy", {})

    @property
    def controls(self) -> dict[str, str]:
        return self.raw.get("controls", {})

    @property
    def rules(self) -> list[dict[str, Any]]:
        return self.raw.get("risk_rules", [])

    def control_text(self, control_id: str) -> str:
        return self.controls.get(control_id, control_id)

    def value_label(self, value_id: str) -> str:
        return self.values.get(value_id, {}).get("label", value_id)

    def keywords_for(self, section: str, key: str) -> list[str]:
        return self.taxonomy.get(section, {}).get(key, [])
