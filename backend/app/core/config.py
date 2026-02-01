import os
import logging

logger = logging.getLogger(__name__)

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not set. Answer generation will fail.")

# Model Configuration
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Retrieval Configuration
CANDIDATE_K = int(os.getenv("CANDIDATE_K", "20"))
MIN_SCORE_THRESHOLD = float(os.getenv("MIN_SCORE_THRESHOLD", "0.40"))
DROP_OFF_THRESHOLD = float(os.getenv("DROP_OFF_THRESHOLD", "0.10"))

# Storage Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "vectordb")
COLLECTION_NAME = "ragex_chunks"

# Generation Configuration
REFUSAL_RESPONSE = "Answer: Not found in indexed documents."
GENERATION_TEMPERATURE = float(os.getenv("GENERATION_TEMPERATURE", "0.1"))
GENERATION_MAX_TOKENS = int(os.getenv("GENERATION_MAX_TOKENS", "500"))
