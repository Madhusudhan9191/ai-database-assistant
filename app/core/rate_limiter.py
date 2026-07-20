import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class InMemoryRateLimiter:
    """
    A lightweight thread-safe in-memory rate limiter using a sliding window.
    Filters out timestamps older than 60 seconds on every check.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.history = defaultdict(list)

    def is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        # Clean history older than 60 seconds
        self.history[client_ip] = [t for t in self.history[client_ip] if now - t < 60]
        
        if len(self.history[client_ip]) >= self.requests_per_minute:
            return True
            
        self.history[client_ip].append(now)
        return False


# Lockout parameters
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

# In-memory tracking structures
_failed_login_attempts = defaultdict(int)
_lockout_timestamps = defaultdict(float)

def check_lockout(username: str) -> tuple[bool, int]:
    """
    Checks if a username is locked out.
    Returns (is_locked, remaining_seconds).
    Resets failed attempts if the lockout duration has passed.
    """
    username = username.strip().lower()
    now = time.time()
    lockout_time = _lockout_timestamps.get(username, 0.0)
    
    if lockout_time > 0.0:
        elapsed = now - lockout_time
        if elapsed < LOCKOUT_DURATION_SECONDS:
            remaining = int(LOCKOUT_DURATION_SECONDS - elapsed)
            return True, remaining
        else:
            # Lockout expired, reset counters
            reset_failed_logins(username)
            
    return False, 0

def register_failed_login(username: str) -> bool:
    """
    Registers a failed login attempt for a username.
    If consecutive failures reach MAX_FAILED_ATTEMPTS, locks the account.
    Returns True if account is newly locked out, False otherwise.
    """
    username = username.strip().lower()
    _failed_login_attempts[username] += 1
    
    if _failed_login_attempts[username] >= MAX_FAILED_ATTEMPTS:
        _lockout_timestamps[username] = time.time()
        logger.warning(f"Account lockout triggered for user: {username} due to {_failed_login_attempts[username]} failed attempts.")
        return True
        
    return False

def reset_failed_logins(username: str):
    """Resets failed attempts and unlocks the username."""
    username = username.strip().lower()
    _failed_login_attempts.pop(username, None)
    _lockout_timestamps.pop(username, None)


# Initialize limiters
login_limiter = InMemoryRateLimiter(requests_per_minute=10) # 10 requests per minute
ask_limiter = InMemoryRateLimiter(requests_per_minute=30)  # 30 requests per minute
