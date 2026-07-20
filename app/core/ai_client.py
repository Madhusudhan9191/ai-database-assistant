from groq import Groq
from app.core.config import settings

# Shared Groq client singleton instance to optimize memory and connection usage
client = Groq(api_key=settings.groq_api_key)

# Shared Database Dialect mapping
DIALECT_MAP = {
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "oracle": "Oracle",
}
