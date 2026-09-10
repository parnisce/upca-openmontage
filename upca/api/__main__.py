"""python -m upca.api"""

from __future__ import annotations

import uvicorn

from upca.api.app import app


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=4760, log_level="info")


if __name__ == "__main__":
    main()
