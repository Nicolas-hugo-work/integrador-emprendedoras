"""La proyección local es 768, normalizada y determinista."""

from app.services.embedding_service import DIMENSION, embed


def test_embed_has_768_unit_components() -> None:
    first = embed("registro de comercio en Bolivia")
    again = embed("registro de comercio en Bolivia")
    other = embed("precio de venta de pan")
    assert len(first) == DIMENSION
    assert first == again
    assert first != other
    norm = sum(value * value for value in first) ** 0.5
    assert abs(norm - 1.0) < 1e-6
