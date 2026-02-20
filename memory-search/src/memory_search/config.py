"""Paths and constants for memory-search."""

from pathlib import Path

# Database
DB_PATH = Path.home() / "assistant" / "data" / "memory.db"

# Vault paths to index
VAULT_ROOT = Path("/mnt/d/BCGVentures_Notes/BCG Ventures")

INDEX_PATHS = [
    VAULT_ROOT / "Claude",
    VAULT_ROOT / "Clients",
    VAULT_ROOT / "Daily Notes",
    VAULT_ROOT / "Internal",
    VAULT_ROOT / "Tools",
]

# Paths to skip
EXCLUDE_DIRS = {
    "Access Keys",
    "Inbox",
    ".obsidian",
    ".trash",
}

# Skill-specific references (in assistant dir)
SKILL_REFS = Path.home() / "assistant" / ".claude" / "skills"

# Embedding
OPENROUTER_URL = "https://openrouter.ai/api/v1/embeddings"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMS = 1536
ENV_API_KEY = "SPROCKET_OPENROUTER_KEY"

# Chunking
CHUNK_TARGET_CHARS = 1600  # ~400 tokens
CHUNK_OVERLAP_CHARS = 320  # ~80 tokens

# Search
DEFAULT_MAX_RESULTS = 6
DEFAULT_MIN_SCORE = 0.005  # RRF scores are small — 1/(rank+60) maxes at ~0.017
VECTOR_WEIGHT = 0.7
BM25_WEIGHT = 0.3
RRF_K = 60  # Reciprocal Rank Fusion constant

# Memory storage
MEMORY_DIR = VAULT_ROOT / "Claude" / "memory"
NOTES_FILE = VAULT_ROOT / "Claude" / "Notes.md"
