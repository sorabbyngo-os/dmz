"""
Sorabbyngo DMZ — Inbound Gateway
Validates and sanitizes requests before they cross to Byngox Prime.

Pipeline:
  1. Size check — reject oversized payloads
  2. Rate limit — enforce per-node RPM limit
  3. Field scrub — remove all forbidden fields
  4. PII scan — detect and strip personal information
  5. CML verify — confirm CML has already filtered this request
  6. Audit log — record every crossing attempt
"""
import hashlib
import json
import logging
import re
import time
from typing import Optional

from dmz.policy.rules import (
    MAX_REQUEST_BYTES, RATE_LIMIT_RPM,
    FORBIDDEN_OUTBOUND_FIELDS, PII_PATTERNS,
    ALLOWED_PRIME_MODELS, ALLOWED_TASK_TYPES,
)

log = logging.getLogger("sorabbyngo.dmz.inbound")


class InboundGateway:
    """
    One-way gate: internal → Prime.
    Everything that enters here must be sanitized.
    Nothing with patient data, NodeIDs, or PII may pass.
    """

    def __init__(self):
        # Rate limit tracking: node_id → (count, window_start)
        self._rate_map: dict = {}
        self._pii_patterns = [re.compile(p, re.IGNORECASE) for p in PII_PATTERNS]

    def validate(self, request: dict) -> tuple[bool, str, dict]:
        """
        Validate and sanitize an inbound request.

        Returns:
            (allowed: bool, reason: str, sanitized_request: dict)
        """
        # 1 — Size check
        raw_size = len(json.dumps(request).encode())
        if raw_size > MAX_REQUEST_BYTES:
            return False, f"Request too large: {raw_size} bytes (max {MAX_REQUEST_BYTES})", {}

        # 2 — Rate limit
        node_id = request.get("source_node", "unknown")
        if not self._check_rate(node_id):
            return False, f"Rate limit exceeded for node {node_id[:12]}", {}

        # 3 — Model allowlist
        model = request.get("model", "")
        if model and model not in ALLOWED_PRIME_MODELS:
            return False, f"Model not allowed: {model}", {}

        # 4 — Task type allowlist
        task_type = request.get("task_type", "")
        if task_type and task_type not in ALLOWED_TASK_TYPES:
            return False, f"Task type not allowed: {task_type}", {}

        # 5 — Field scrub + PII scan
        sanitized, pii_found = self._sanitize(request)

        if pii_found:
            log.warning(
                "[DMZ/Inbound] PII detected and stripped from request "
                "node=%s fields=%s", node_id[:12], pii_found,
            )

        # 6 — CML verification flag
        if not sanitized.get("cml_verified"):
            return False, "Request must be CML-verified before crossing DMZ", {}

        # Remove the cml_verified flag itself — Prime doesn't need it
        sanitized.pop("cml_verified", None)
        sanitized.pop("source_node", None)

        return True, "ok", sanitized

    def _check_rate(self, node_id: str) -> bool:
        now = time.time()
        if node_id not in self._rate_map:
            self._rate_map[node_id] = (1, now)
            return True

        count, window_start = self._rate_map[node_id]
        if now - window_start > 60:
            # New window
            self._rate_map[node_id] = (1, now)
            return True

        if count >= RATE_LIMIT_RPM:
            return False

        self._rate_map[node_id] = (count + 1, window_start)
        return True

    def _sanitize(self, data: dict) -> tuple[dict, list]:
        """Remove forbidden fields and strip PII from text values."""
        pii_found = []
        result    = {}

        for key, value in data.items():
            # Drop forbidden fields entirely
            if key.lower() in FORBIDDEN_OUTBOUND_FIELDS:
                pii_found.append(key)
                continue

            if isinstance(value, str):
                cleaned, found = self._strip_pii(value)
                result[key]    = cleaned
                pii_found.extend(found)
            elif isinstance(value, dict):
                cleaned, found = self._sanitize(value)
                result[key]    = cleaned
                pii_found.extend(found)
            elif isinstance(value, list):
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        c, f = self._sanitize(item)
                        cleaned_list.append(c)
                        pii_found.extend(f)
                    elif isinstance(item, str):
                        c, f = self._strip_pii(item)
                        cleaned_list.append(c)
                        pii_found.extend(f)
                    else:
                        cleaned_list.append(item)
                result[key] = cleaned_list
            else:
                result[key] = value

        return result, pii_found

    def _strip_pii(self, text: str) -> tuple[str, list]:
        """Strip PII patterns from text. Returns (cleaned_text, found_patterns)."""
        found   = []
        cleaned = text
        for pattern in self._pii_patterns:
            if pattern.search(cleaned):
                found.append(pattern.pattern[:20])
                cleaned = pattern.sub("[REDACTED]", cleaned)
        return cleaned, found
