"""Proyección léxica local a 768 dimensiones. Sin proveedor de red ni LLM."""

import hashlib
import math
import re

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.models.base import new_uuid7
from app.models.rag import EmbeddingModel, SourceChunk, SourceChunkEmbedding

MODEL_CODE = "lexical-hash-768"
DIMENSION = 768
_TOKEN = re.compile(r"[a-záéíóúñ0-9]+")


def embed(text_value: str) -> list[float]:
    """Hashea cada token a un eje y normaliza. Determinista, sin artefactos."""
    vector = [0.0] * DIMENSION
    for token in _TOKEN.findall(text_value.casefold()):
        if len(token) < 4:
            continue
        digest = hashlib.sha256(token.encode()).digest()
        for offset in range(0, 24, 4):
            raw = int.from_bytes(digest[offset : offset + 4], "little")
            index = raw % DIMENSION
            sign = 1.0 if (raw >> 31) == 0 else -1.0
            vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def as_vec_text(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def active_model(db: Session) -> EmbeddingModel:
    row = db.scalar(select(EmbeddingModel).where(EmbeddingModel.code == MODEL_CODE))
    if row:
        return row
    row = EmbeddingModel(
        code=MODEL_CODE,
        provider="local",
        model_name="lexical-hash",
        model_version="1",
        dimension=DIMENSION,
        distance_metric="COSINE",
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def persist_chunk_embedding(db: Session, chunk: SourceChunk) -> None:
    """Escribe o reemplaza el vector del fragmento."""
    model = active_model(db)
    existing = db.scalar(
        select(SourceChunkEmbedding).where(SourceChunkEmbedding.source_chunk_id == chunk.id)
    )
    payload = as_vec_text(embed(f"{chunk.heading or ''} {chunk.content}"))
    if existing:
        db.execute(
            text(
                "UPDATE source_chunk_embeddings SET embedding = VEC_FromText(:vec), "
                "updated_at = :now WHERE id = :id"
            ),
            {"vec": payload, "now": utc_now(), "id": existing.id},
        )
        return
    db.execute(
        text(
            "INSERT INTO source_chunk_embeddings "
            "(id, source_chunk_id, embedding_model_id, embedding, created_at, updated_at) "
            "VALUES (:id, :chunk_id, :model_id, VEC_FromText(:vec), :now, :now)"
        ),
        {
            "id": new_uuid7(),
            "chunk_id": chunk.id,
            "model_id": model.id,
            "vec": payload,
            "now": utc_now(),
        },
    )
