"""
Sorabbyngo DMZ — Main Service
NATS-based data diode between internal network and Byngox Prime.

Subscribes to: sorabbyngo.dmz.request
Forwards to:   Byngox Prime vLLM API
Returns to:    sorabbyngo.dmz.result

Every crossing is audited via sorabbyngo.dmz.audit
"""
import asyncio
import json
import logging
import os
import time
import urllib.request
from datetime import datetime, timezone

import nats

from dmz.inbound.gateway import InboundGateway
from dmz.outbound.gateway import OutboundGateway

log = logging.getLogger("sorabbyngo.dmz")

NATS_URL   = os.environ.get("NATS_URL",       "nats://localhost:4222")
PRIME_URL  = os.environ.get("BYNGOX_PRIME_URL","http://byngox-prime.internal:8000/v1/chat/completions")
PRIME_KEY  = os.environ.get("BYNGOX_PRIME_KEY","")

SUBJECTS = {
    "request":  "sorabbyngo.dmz.request",
    "result":   "sorabbyngo.dmz.result",
    "rejected": "sorabbyngo.dmz.rejected",
    "audit":    "sorabbyngo.dmz.audit",
}

BANNER = """
╔══════════════════════════════════════════════════════════╗
║       Sorabbyngo DMZ — One-Way Wall                      ║
║       Internal ──▶ Prime  ·  No reverse channel          ║
╚══════════════════════════════════════════════════════════╝
"""


class DMZService:
    def __init__(self):
        self._nc       = None
        self._inbound  = InboundGateway()
        self._outbound = OutboundGateway()
        self._running  = False
        self._stats    = {"requests": 0, "allowed": 0, "rejected": 0, "errors": 0}

    async def start(self):
        self._running = True
        print(BANNER)

        self._nc = await nats.connect(
            NATS_URL,
            name="sorabbyngo-dmz",
            max_reconnect_attempts=-1,
        )
        log.info("DMZ Service connected to NATS")
        await self._nc.subscribe(SUBJECTS["request"], cb=self._handle_request)
        log.info("DMZ listening on %s", SUBJECTS["request"])

        while self._running:
            await asyncio.sleep(60)
            log.info(
                "[DMZ] Stats: requests=%d allowed=%d rejected=%d errors=%d",
                self._stats["requests"], self._stats["allowed"],
                self._stats["rejected"], self._stats["errors"],
            )

    async def _handle_request(self, msg):
        self._stats["requests"] += 1
        request_id = f"dmz-{time.time():.6f}"

        try:
            data = json.loads(msg.data.decode())
        except Exception:
            await self._reject(request_id, {}, "Invalid JSON")
            return

        # Inbound validation
        allowed, reason, sanitized = self._inbound.validate(data)
        if not allowed:
            log.warning("[DMZ] Request rejected: %s", reason)
            self._stats["rejected"] += 1
            await self._reject(request_id, data, reason)
            return

        self._stats["allowed"] += 1
        log.info("[DMZ] Request allowed → Prime (id=%s)", request_id[:16])

        # Forward to Prime
        try:
            raw_result = await self._call_prime(sanitized)
        except Exception as e:
            log.error("[DMZ] Prime call failed: %s", e)
            self._stats["errors"] += 1
            await self._reject(request_id, sanitized, f"Prime unreachable: {e}")
            return

        # Outbound validation
        result_ok, result_reason, clean_result = self._outbound.validate(
            raw_result, request_id
        )
        if not result_ok:
            log.warning("[DMZ] Result rejected: %s", result_reason)
            self._stats["errors"] += 1
            await self._reject(request_id, {}, f"Result invalid: {result_reason}")
            return

        # Return result to internal network
        await self._nc.publish(
            SUBJECTS["result"],
            json.dumps(clean_result).encode(),
        )

        # Audit
        await self._audit(request_id, "ALLOWED", sanitized, clean_result)
        log.info("[DMZ] Result returned to internal network (id=%s)", request_id[:16])

    async def _call_prime(self, request: dict) -> dict:
        """Forward sanitized request to Byngox Prime vLLM."""
        model  = request.get("model", "deepseek-r1:70b")
        prompt = request.get("prompt", "")

        payload = json.dumps({
            "model":      model,
            "max_tokens": 1024,
            "messages":   [{"role": "user", "content": prompt}],
        }).encode()

        headers = {"Content-Type": "application/json"}
        if PRIME_KEY:
            headers["Authorization"] = f"Bearer {PRIME_KEY}"

        req = urllib.request.Request(PRIME_URL, data=payload, headers=headers)
        loop = asyncio.get_event_loop()

        def _post():
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())

        result = await loop.run_in_executor(None, _post)
        return {
            "response": result["choices"][0]["message"]["content"],
            "model":    model,
            "status":   "ok",
        }

    async def _reject(self, request_id: str, data: dict, reason: str):
        await self._nc.publish(
            SUBJECTS["rejected"],
            json.dumps({
                "request_id": request_id,
                "reason":     reason,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            }).encode(),
        )
        await self._audit(request_id, "REJECTED", data, {}, reason)

    async def _audit(self, request_id: str, action: str,
                     request: dict, result: dict, reason: str = ""):
        await self._nc.publish(
            SUBJECTS["audit"],
            json.dumps({
                "request_id":   request_id,
                "action":       action,
                "reason":       reason,
                "timestamp":    datetime.now(timezone.utc).isoformat(),
                "request_size": len(json.dumps(request)),
                "result_size":  len(json.dumps(result)),
                "model":        request.get("model", ""),
                "task_type":    request.get("task_type", ""),
            }).encode(),
        )

    def stop(self):
        self._running = False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    asyncio.run(DMZService().start())
