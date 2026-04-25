<p align="center">
  <img src="./assets/banner.svg" alt="Sorabbyngo DMZ" width="800"/>
</p>

<p align="center">
  <strong>Sorabbyngo DMZ — One-Way Wall</strong><br/>
  Byngox Prime isolation · Data diode · No reverse channel
</p>

<p align="center">
  <img src="https://img.shields.io/badge/pattern-data%20diode-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/privacy-no%20patient%20data-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/identity-no%20NodeID-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/audit-every%20crossing-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/consent-opt--in%20only-yellow?style=flat-square"/>
</p>

---

The DMZ is a one-way data wall between the Sorabbyngo internal network and Byngox Prime — the self-hosted H100/A100 inference cluster. Data flows **in** to Prime. Results flow **out**. Nothing else crosses.

No patient data. No NodeIDs. No behavioral logs. No raw telemetry. Only sanitized, CML-filtered inference requests reach Prime. Only model outputs return — never raw model weights, never training data.

---

## Data flow

```mermaid
graph LR
    INT["Sorabbyngo\nInternal Network\nByngox · Novela · Chameha\nCML · Sentinel"]

    subgraph dmz["DMZ — One-Way Wall"]
        IN["Inbound Gateway\nCML verify\nPII check\nsize limit"]
        POL["Policy Engine\ndata diode\nrate limit\nallow / deny"]
        OUT["Outbound Gateway\nresult validator\nstrip metadata"]
    end

    PRIME["Byngox Prime\nSelf-hosted H100/A100\nDeepSeek-R1 70B\nMixtral 8x22B"]

    INT -->|CML-filtered requests only| IN
    IN --> POL --> OUT
    OUT -->|results only| PRIME
    PRIME -.->|no reverse channel| OUT

    style INT   fill:#0d0d00,stroke:#ffee00,color:#ffee44
    style IN    fill:#0d0d00,stroke:#ccbb00,color:#ffee44
    style POL   fill:#0d0d00,stroke:#ccbb00,color:#ffee44
    style OUT   fill:#0d0d00,stroke:#ccbb00,color:#ffee44
    style PRIME fill:#0d0500,stroke:#886600,color:#ccaa33
```

---

## Rules

| Rule | Description |
|---|---|
| No patient identifiers | Names, IDs, DOB, phone numbers stripped by CML before inbound gateway |
| No NodeID | Hardware identity never reaches Prime |
| No reverse channel | Prime cannot initiate connections inward |
| Rate limited | Max 100 requests per minute per node |
| Audit every crossing | Every request and response logged with SUID |
| Results validated | Prime output checked before returning inward |
| Opt-in only | Cloud/Prime calls require explicit user consent — ADR-009 |

---

## NATS subjects

| Subject | Direction | Purpose |
|---|---|---|
| `sorabbyngo.dmz.request` | Internal → DMZ | Sanitized inference request |
| `sorabbyngo.dmz.result` | DMZ → Internal | Validated inference result |
| `sorabbyngo.dmz.rejected` | DMZ → Internal | Rejected request + reason |
| `sorabbyngo.dmz.audit` | DMZ → Sentinel | Every crossing logged |

---

## What never crosses

```mermaid
graph TD
    NEVER["What never crosses the DMZ"]
    NEVER --> A["Patient names, IDs, DOB, phone numbers"]
    NEVER --> B["Hardware NodeID"]
    NEVER --> C["Behavioral logs or raw telemetry"]
    NEVER --> D["Model weights or training data"]
    NEVER --> E["Reverse connections from Prime"]

    style NEVER fill:#1a0000,stroke:#ff2200,color:#ff6666
    style A fill:#0d0000,stroke:#cc0000,color:#ff4444
    style B fill:#0d0000,stroke:#cc0000,color:#ff4444
    style C fill:#0d0000,stroke:#cc0000,color:#ff4444
    style D fill:#0d0000,stroke:#cc0000,color:#ff4444
    style E fill:#0d0000,stroke:#cc0000,color:#ff4444
```

---

## Request lifecycle

```mermaid
sequenceDiagram
    participant C as Chameha / Byngox
    participant CML as CML Layer
    participant DMZ as DMZ Gateway
    participant P as Byngox Prime

    C->>CML: Raw inference request
    CML->>CML: Strip PII · safety check
    CML->>DMZ: Sanitized request
    DMZ->>DMZ: Policy check · rate limit · size check
    DMZ->>P: Clean request (no identity)
    P->>DMZ: Model output
    DMZ->>DMZ: Validate result · strip metadata
    DMZ->>C: Clean result + audit log → Sentinel
```

---

## Related repositories

| Repo | Role |
|---|---|
| `cml` | Sanitizes all requests before they reach the DMZ |
| `byngox` | Swarm engine — only Tier 4 calls cross the DMZ |
| `sentinel-runtime` | Receives audit log of every DMZ crossing |
| `identity-core` | SUID used to trace every crossing without exposing identity |
| `security` | DMZ enforces Ring 4 AI safety boundary |

---

<p align="center">
  <strong>Sorabbyngo Company</strong> · Kisii, Kenya · 2026<br/>
  <em>Rhythm of Digital Life</em>
</p>
