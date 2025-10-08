from __future__ import annotations

import json
from pathlib import Path

from .main import app

def main() -> None:
    """Generate OpenAPI schema to interfaces/openapi.json."""
    schema = app.openapi()
    out_path = Path(__file__).resolve().parents[2] / "interfaces" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schema, indent=2))
    print(f"Wrote OpenAPI to {out_path}")

if __name__ == "__main__":
    main()
