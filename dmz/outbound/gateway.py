"""
Sorabbyngo DMZ — Outbound Gateway
Validates results coming back from Byngox Prime before
returning them to the internal network.

Prime results must:
  - Not exceed size limit
  - Not contain unexpected metadata
  - Pass basic sanity check (valid JSON structure)
  - Be stripped of any Prime-internal fields
"""
import json
import logging
from dmz.policy.rules import MAX_RESULT_BYTES

log = logging.getLogger("sorabbyngo.dmz.outbound")

# Fields Prime should never return — strip them
STRIP_FROM_RESULTS = {
    "server_id", "cluster_id", "gpu_id",
    "processing_node", "internal_id",
    "request_id_internal",
}

# Required fields in a valid Prime result
REQUIRED_RESULT_FIELDS = {"response"}


class OutboundGateway:
    """
    One-way gate: Prime → internal.
    Validates and cleans Prime results before they re-enter the network.
    """

    def validate(self, result: dict, original_request_id: str = "") -> tuple[bool, str, dict]:
        """
        Validate an outbound result from Prime.

        Returns:
            (allowed: bool, reason: str, cleaned_result: dict)
        """
        # 1 — Size check
        raw_size = len(json.dumps(result).encode())
        if raw_size > MAX_RESULT_BYTES:
            return False, f"Result too large: {raw_size} bytes (max {MAX_RESULT_BYTES})", {}

        # 2 — Required fields
        for field in REQUIRED_RESULT_FIELDS:
            if field not in result:
                return False, f"Missing required field in result: {field}", {}

        # 3 — Strip internal Prime metadata
        cleaned = {
            k: v for k, v in result.items()
            if k not in STRIP_FROM_RESULTS
        }

        # 4 — Attach request tracking
        if original_request_id:
            cleaned["request_id"] = original_request_id

        log.debug(
            "[DMZ/Outbound] Result validated — size=%d bytes request=%s",
            raw_size, original_request_id[:12] if original_request_id else "?",
        )

        return True, "ok", cleaned
