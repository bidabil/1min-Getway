"""`python -m gateway`: run the server with uvicorn."""

import uvicorn

from .config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "gateway.main:app",
        host=settings.host,
        port=settings.port,
        proxy_headers=True,
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
