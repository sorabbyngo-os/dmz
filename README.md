<p align="center">
  <img src="https://raw.odolocharles@gmail.com/sorabbyngo-Labs/.github/main/assets/sorabbyngo-logo.jpg" width="480"/>
</p>
<p align="center">
  <strong>Sorabbyngo DMZ — One-Way Wall</strong>
</p>
<p align="center">
  Byngox Prime isolation · Data diode · No reverse channel
</p>

---

## What this is

The DMZ is a one-way data wall between the Sorabbyngo internal network
and Byngox Prime (the self-hosted H100/A100 inference cluster).

**Data flows IN to Prime. Results flow OUT. Nothing else crosses.**

No patient data. No NodeIDs. No behavioral logs. No raw telemetry.
Only sanitized, CML-filtered inference requests reach Prime.
Only model outputs return — never raw model weights, never training data.

---

## Architecture
┌─────────────────────────────────────────────────────────┐
│                 Sorabbyngo Internal Network              │
│  Byngox · Novela · Chameha · CML · Sentinel             │
└────────────────────┬────────────────────────────────────┘
│ CML-filtered requests only
▼
┌─────────────────────────────────────────────────────────┐
│                        DMZ                              │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐   ┌────────────┐  │
│  │  Inbound    │    │   Policy     │   │  Outbound  │  │
│  │  Gateway    │───▶│   Engine     │──▶│  Gateway   │  │
│  │             │    │              │   │            │  │
│  │ CML verify  │    │ data diode   │   │ result     │  │
│  │ PII check   │    │ rate limit   │   │ validator  │  │
│  │ size limit  │    │ allow/deny   │   │ strip meta │  │
│  └─────────────┘    └──────────────┘   └─────┬──────┘  │
│                                               │         │
└───────────────────────────────────────────────┼─────────┘
│ results only
▼
┌─────────────────────────────────────────────────────────┐
│                   Byngox Prime                          │
│            Self-hosted H100/A100 cluster                │
│         DeepSeek-R1 70B · Mixtral 8x22B                 │
└─────────────────────────────────────────────────────────┘
---

## Rules

1. **No patient identifiers cross the DMZ** — names, IDs, DOB, phone numbers stripped by CML before inbound gateway
2. **No NodeID crosses the DMZ** — hardware identity never reaches Prime
3. **No reverse channel** — Prime cannot initiate connections inward
4. **Rate limited** — max 100 requests/minute per node
5. **Audit every crossing** — every request/response logged with SUID
6. **Results validated** — Prime output checked before returning inward
7. **Opt-in only** — cloud/Prime calls require explicit user consent (ADR-009)

---

## NATS Subjects

| Subject | Direction | Purpose |
|---|---|---|
| `sorabbyngo.dmz.request` | Internal → DMZ | Sanitized inference request |
| `sorabbyngo.dmz.result` | DMZ → Internal | Validated inference result |
| `sorabbyngo.dmz.rejected` | DMZ → Internal | Rejected request + reason |
| `sorabbyngo.dmz.audit` | DMZ → Sentinel | Every crossing logged |

---

**Sorabbyngo Company** · Kisii, Kenya · 2026
*Rhythm of Digital Life*
