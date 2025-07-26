# Reliability Configuration for Agentic AI System

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
EXPONENTIAL_BACKOFF = True

# Timeout Configuration
API_TIMEOUT = 10  # seconds
LLM_TIMEOUT = 30  # seconds

# Agent Configuration
MAX_AGENT_ITERATIONS = 30
AGENT_EARLY_STOPPING = "generate"

# Error Handling
FALLBACK_ENABLED = True
FALLBACK_CREDIT_SCORE = 650
FALLBACK_RESPONSES = {
    "api_error": "API temporarily unavailable. Using default values.",
    "llm_error": "LLM service temporarily unavailable. Using fallback logic.",
    "parsing_error": "Unable to parse response. Using default format.",
    "timeout_error": "Request timed out. Please try again.",
}

# Logging Configuration
VERBOSE_LOGGING = True
DEBUG_MODE = False
LOG_RETRIES = True
LOG_FALLBACKS = True

# Rate Limiting
MIN_REQUEST_INTERVAL = 1.0  # seconds between requests
RATE_LIMIT_BACKOFF = 2.0  # seconds to wait on rate limit

# Workflow Configuration
WORKFLOW_TIMEOUT = 300  # 5 minutes maximum for entire workflow
STEP_TIMEOUT = 60  # 1 minute maximum per step
