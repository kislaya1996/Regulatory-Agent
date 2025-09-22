#!/usr/bin/env python3
"""
Rate limiting configuration for the regulatory document analysis system.
This helps prevent API throttling by managing request rates.
"""

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    # LLM calls per minute
    'llm_calls_per_minute': 20,
    
    # Summary tool calls per minute
    'summary_calls_per_minute': 15,
    
    # Vector tool calls per minute
    'vector_calls_per_minute': 10,
    
    # Maximum parallel workers
    'max_parallel_workers': 3,
    
    # Retry settings
    'max_retries': 3,
    'base_retry_delay': 2,  # seconds
    'max_retry_delay': 10,  # seconds
    
    # Jitter settings (random delay to avoid thundering herd)
    'min_jitter': 0.1,  # seconds
    'max_jitter': 0.5,  # seconds
}

# Throttling detection patterns
THROTTLING_PATTERNS = [
    "ThrottlingException",
    "Too many requests",
    "rate limit",
    "throttled",
    "429",  # HTTP status code for too many requests
]

# Performance optimization settings
PERFORMANCE_CONFIG = {
    # Fast mode settings
    'fast_mode': {
        'max_docs_to_analyze': 8,  # Reduced from 10
        'max_docs_to_query': 2,    # Reduced from 3
        'max_workers': 2,          # Reduced from 3
    },
    
    # Comprehensive mode settings
    'comprehensive_mode': {
        'max_docs_to_analyze': 15, # Reduced from 20
        'max_docs_to_query': 3,    # Reduced from 5
        'max_workers': 3,          # Keep at 3
    },
    
    # Progress reporting
    'progress_interval': 2,  # Report progress every N documents
}

def get_rate_limit_config():
    """Get the current rate limit configuration."""
    return RATE_LIMIT_CONFIG

def get_performance_config():
    """Get the current performance configuration."""
    return PERFORMANCE_CONFIG

def is_throttling_error(error_message):
    """Check if an error message indicates throttling."""
    error_lower = error_message.lower()
    return any(pattern.lower() in error_lower for pattern in THROTTLING_PATTERNS)

def calculate_retry_delay(attempt, base_delay=2, max_delay=10):
    """Calculate exponential backoff delay for retries."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay

def get_optimal_workers(doc_count, mode='fast'):
    """Get optimal number of workers based on document count and mode."""
    config = PERFORMANCE_CONFIG.get(f'{mode}_mode', PERFORMANCE_CONFIG['fast_mode'])
    max_workers = config.get('max_workers', 2)
    return min(max_workers, doc_count)

def get_doc_limits(mode='fast'):
    """Get document limits for the specified mode."""
    config = PERFORMANCE_CONFIG.get(f'{mode}_mode', PERFORMANCE_CONFIG['fast_mode'])
    return {
        'max_docs_to_analyze': config.get('max_docs_to_analyze', 8),
        'max_docs_to_query': config.get('max_docs_to_query', 2),
    } 