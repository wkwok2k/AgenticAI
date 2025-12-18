import os, json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from jinja2 import Environment, StrictUndefined

from vertexai.generative_models import GenerativeModel, GenerationConfig


class VertexGenAI:
    def __init__(self):
        # init auth etc.
        pass

    def _load_agent_config(self, agent_config_name: str) -> Dict[str, Any]:
        cfg_dir = Path(__file__).resolve().parents[1] / "agents" / "configs"
        cfg_path = cfg_dir / f"{agent_config_name}.yml"
        if not cfg_path.exists():
            raise FileNotFoundError(f"Agent config not found: {cfg_path}")

        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg

    def _render(self, template: str, template_vars: Dict[str, Any]) -> str:
        env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
        return env.from_string(template).render(**(template_vars or {}))

