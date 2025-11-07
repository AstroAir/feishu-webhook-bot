"""FastAPI-based event ingestion server for Feishu webhook callbacks."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import threading
from collections.abc import Callable
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from .config import EventServerConfig
from .logger import get_logger

logger = get_logger("event_server")

EventHandler = Callable[[dict[str, Any]], None]


class EventServer:
    """Serve Feishu event callbacks and forward them to the bot."""

    def __init__(self, config: EventServerConfig, handler: EventHandler) -> None:
        self._config = config
        self._handler = handler
        self._app = FastAPI()
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._create_routes()

    # ------------------------------------------------------------------
    # FastAPI setup
    # ------------------------------------------------------------------
    def _create_routes(self) -> None:
        @self._app.get("/healthz")
        async def health() -> dict[str, str]:  # pragma: no cover - trivial
            return {"status": "ok"}

        @self._app.post(self._config.path)
        async def receive_event(request: Request) -> dict[str, str]:
            payload = await request.json()
            self._verify_token(payload)
            body = await request.body()
            self._verify_signature(request, body)

            if payload.get("type") == "url_verification":
                return {"challenge": payload.get("challenge", "")}

            try:
                self._handler(payload)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Event handler failure: %s", exc, exc_info=True)
                raise HTTPException(status_code=500, detail="Handler failure") from exc

            return {"status": "ok"}

    # ------------------------------------------------------------------
    # Security helpers
    # ------------------------------------------------------------------
    def _verify_token(self, payload: dict[str, Any]) -> None:
        token = self._config.verification_token
        if not token:
            return
        if payload.get("token") != token:
            raise HTTPException(status_code=403, detail="Invalid verification token")

    def _verify_signature(self, request: Request, body: bytes) -> None:
        secret = self._config.signature_secret
        if not secret:
            return

        signature = request.headers.get("X-Lark-Signature")
        timestamp = request.headers.get("X-Lark-Request-Timestamp")
        nonce = request.headers.get("X-Lark-Request-Nonce")
        if not signature or not timestamp or not nonce:
            raise HTTPException(status_code=403, detail="Missing signature headers")

        message = (timestamp + nonce).encode("utf-8") + body
        digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
        computed = base64.b64encode(digest).decode("utf-8")
        if not hmac.compare_digest(signature, computed):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread or not self._config.enabled:
            return

        config = uvicorn.Config(
            self._app,
            host=self._config.host,
            port=self._config.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)

        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                server = self._server
                if server is None:
                    logger.error("Event server thread started without a uvicorn server instance")
                    return
                loop.run_until_complete(server.serve())
            finally:
                loop.close()

        self._thread = threading.Thread(
            target=_run,
            name="feishu-event-server",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Feishu event server listening on http://%s:%s%s",
            self._config.host,
            self._config.port,
            self._config.path,
        )

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Feishu event server stopped")

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
