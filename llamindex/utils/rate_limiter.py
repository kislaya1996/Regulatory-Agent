import time
import threading

class TokenBucket:
    def __init__(self, capacity, refill_rate_per_second):
        """
        Initializes a TokenBucket for rate limiting.

        Args:
            capacity (int): The maximum number of tokens the bucket can hold.
            refill_rate_per_second (float): The rate at which tokens are added to the bucket per second.
        """
        self.capacity = capacity
        self.tokens = capacity  # Start with a full bucket
        self.refill_rate_per_second = refill_rate_per_second
        self.last_refill_time = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self):
        """Refills the token bucket based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill_time
        
        # Calculate tokens to add, ensuring we don't exceed capacity
        tokens_to_add = elapsed * self.refill_rate_per_second
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill_time = now

    def try_acquire(self, tokens_needed=1):
        """
        Attempts to acquire tokens.

        Args:
            tokens_needed (int): The number of tokens required for the operation.

        Returns:
            bool: True if tokens were acquired, False otherwise.
        """
        with self.lock:
            self._refill()  # Always refill before trying to acquire
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return True
            return False

    def acquire(self, tokens_needed=1):
        """
        Acquires tokens, blocking if necessary until tokens are available.

        Args:
            tokens_needed (int): The number of tokens required for the operation.
        """
        while True:
            with self.lock:
                self._refill()
                if self.tokens >= tokens_needed:
                    self.tokens -= tokens_needed
                    return
            # If no tokens, wait a small amount of time before retrying
            time.sleep(0.1)