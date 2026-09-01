from app.security import (
    create_access_token,
    decode_access_token,
    decrypt_text,
    encrypt_text,
    hash_password,
    hash_token,
    verify_password,
)


def test_argon2_password_roundtrip() -> None:
    password_hash = hash_password("una-clave-segura-2026")
    assert password_hash.startswith("$argon2")
    assert verify_password(password_hash, "una-clave-segura-2026")
    assert not verify_password(password_hash, "otra-clave-segura")


def test_access_token_contains_subject() -> None:
    user_id = "01990000-0000-7000-8000-000000000099"
    assert decode_access_token(create_access_token(user_id)) == user_id


def test_sensitive_text_is_encrypted() -> None:
    clear_text = "Nota financiera privada"
    ciphertext = encrypt_text(clear_text)
    assert clear_text not in ciphertext
    assert decrypt_text(ciphertext) == clear_text


def test_token_hash_is_deterministic_without_storing_token() -> None:
    token = "token-temporal"
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
