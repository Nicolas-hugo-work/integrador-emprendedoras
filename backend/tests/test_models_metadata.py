from app.models import Base


def test_metadata_contains_all_tables() -> None:
    assert len(Base.metadata.tables) == 62


def test_vector_and_fulltext_targets_exist() -> None:
    chunks = Base.metadata.tables["source_chunks"]
    embeddings = Base.metadata.tables["source_chunk_embeddings"]
    assert {"heading", "content"}.issubset(chunks.columns.keys())
    assert str(embeddings.columns["embedding"].type) == "VECTOR(768)"


def test_sensitive_ownership_columns_exist() -> None:
    for table_name in ("financial_movements", "conversations", "generated_contents"):
        assert "user_id" in Base.metadata.tables[table_name].columns


def test_core_unique_constraints_exist() -> None:
    contacts = Base.metadata.tables["user_contacts"]
    messages = Base.metadata.tables["messages"]
    contact_constraints = {constraint.name for constraint in contacts.constraints}
    message_constraints = {constraint.name for constraint in messages.constraints}
    assert "uq_contact_type_value" in contact_constraints
    assert "uq_message_sequence" in message_constraints

