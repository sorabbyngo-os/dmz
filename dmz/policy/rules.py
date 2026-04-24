"""
Sorabbyngo DMZ — Policy Rules
Defines what is allowed to cross the DMZ in each direction.
All rules are evaluated before any data leaves the internal network.
"""

# Maximum request size in bytes — prevents data exfiltration via oversized payloads
MAX_REQUEST_BYTES = 8192

# Maximum result size in bytes
MAX_RESULT_BYTES  = 32768

# Rate limiting — requests per minute per node
RATE_LIMIT_RPM = 100

# Fields that must NEVER appear in outbound requests
FORBIDDEN_OUTBOUND_FIELDS = {
    "node_id",
    "nodeid",
    "patient_id",
    "patient_name",
    "name",
    "phone",
    "phone_number",
    "email",
    "date_of_birth",
    "dob",
    "national_id",
    "passport",
    "ip_address",
    "mac_address",
    "location",
    "gps",
    "latitude",
    "longitude",
    "actor_id",
    "user_id",
    "doctor_id",
    "suid",
}

# Patterns that indicate PII in text fields
PII_PATTERNS = [
    r'\b\d{8}\b',                           # National ID (8 digits)
    r'\+254\d{9}',                          # Kenya phone
    r'\+[1-9]\d{1,14}',                     # International phone
    r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',  # Email
    r'\b\d{4}-\d{2}-\d{2}\b',              # Date of birth pattern
    r'[A-Z]{3}-\d{8}-[A-Z]{2}\d{3}-[A-Z0-9]{6}',   # SUID pattern
]

# Allowed Prime models — reject requests for unknown models
ALLOWED_PRIME_MODELS = {
    "deepseek-r1:70b",
    "mixtral:8x22b",
    "llama3.1:70b",
    "meditron:70b",
}

# Allowed task types — reject unknown task types
ALLOWED_TASK_TYPES = {
    "clinical_reasoning",
    "drug_verification",
    "risk_assessment",
    "counterfeit_analysis",
    "population_health",
    "language_translation",
    "summarization",
}
