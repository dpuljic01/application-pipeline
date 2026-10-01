from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models.llm_cache import LLMCache


class LLMCacheRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, *, cache_key: str) -> dict | None:
        entry = self.db.get(LLMCache, cache_key)
        return entry.result if entry else None

    def put(self, *, cache_key: str, operation: str, result: dict) -> None:
        # Two concurrent parses of the same posting both miss, both call the
        # LLM, and both try to insert - the second one is a harmless no-op.
        self.db.execute(
            insert(LLMCache)
            .values(cache_key=cache_key, operation=operation, result=result)
            .on_conflict_do_nothing(index_elements=[LLMCache.cache_key])
        )
