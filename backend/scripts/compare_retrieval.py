"""Corre el mismo conjunto con la recuperación vieja y con la nueva.

Es el entregable de `v0.7.0`. Sin esto, «la recuperación mejoró» sería una
afirmación; con esto es un par de columnas.

`v1` es el `LIKE '%término%'` que la aplicación usó desde `v0.1.0`. Se conserva
aquí, y solo aquí, para poder medir contra qué se compara. No lo llama nadie más
y no vuelve a la aplicación: es material de laboratorio.

    ./.venv/Scripts/python.exe -m scripts.seed_evaluation_set
    ./.venv/Scripts/python.exe -m scripts.compare_retrieval
"""

import argparse
from contextlib import contextmanager

from sqlalchemy import or_, select

from app.config import get_settings
from app.database import SessionLocal
from app.models.admin_research import EvaluationSet
from app.models.identity import Permission, Role, RolePermission, User, UserRole
from app.models.rag import Source, SourceChunk, SourcePublisher, SourceVersion
from app.services import assistant_service, evaluation_service
from scripts.seed_evaluation_set import SET_NAME, SET_VERSION, seed


def _retrieve_with_like(db, terms: list[str]) -> list:
    """La recuperación de `v0.1.0`, tal cual era.

    Tres fragmentos cualesquiera entre los que contengan alguna subcadena, en el
    orden que devuelva la base. Sin términos, devolvía tres publicados al azar.
    """
    query = (
        select(SourceChunk, SourceVersion, Source, SourcePublisher)
        .join(SourceVersion, SourceVersion.id == SourceChunk.source_version_id)
        .join(Source, Source.id == SourceVersion.source_id)
        .join(SourcePublisher, SourcePublisher.id == Source.publisher_id)
        .where(SourceVersion.status == "PUBLISHED", Source.status == "PUBLISHED")
        .limit(3)
    )
    conditions = [SourceChunk.content.like(f"%{term}%") for term in terms[:8]]
    if conditions:
        query = query.where(or_(*conditions))
    return db.execute(query).all()


@contextmanager
def legacy_retrieval():
    """Devuelve el asistente a `v1` mientras dure el bloque."""
    original = assistant_service._retrieve_published
    version = assistant_service.MODEL_VERSION
    assistant_service._retrieve_published = _retrieve_with_like
    assistant_service.MODEL_VERSION = "v1"
    try:
        yield
    finally:
        assistant_service._retrieve_published = original
        assistant_service.MODEL_VERSION = version


def _curator(db) -> User:
    """Cualquier cuenta con `source.review`; el banco exige ese permiso."""
    usuaria = db.scalar(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(RolePermission, RolePermission.role_id == UserRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Permission.code == "source.review", User.deleted_at.is_(None))
        .limit(1)
    )
    if usuaria is None:
        raise SystemExit(
            "No hay ninguna cuenta con source.review. "
            "Ejecuta primero: python -m scripts.seed_test_users"
        )
    return usuaria


def _rates(run) -> dict[str, float]:
    total = len(run.results) or 1
    return {
        "pasan": sum(1 for r in run.results if r.passed) / total,
        "recall": sum(r.retrieval_recall for r in run.results) / total,
        "citan": sum(1 for r in run.results if r.citation_present) / total,
        "advierten": sum(1 for r in run.results if r.warning_complete) / total,
        "se abstienen": sum(1 for r in run.results if r.abstained) / total,
    }


def _print_comparison(v1, v2) -> None:
    izquierda, derecha = _rates(v1), _rates(v2)
    print(f"\nConjunto: {v1.evaluation_set_name} v{v1.evaluation_set_version}")
    print(f"Casos: {len(v1.results)}\n")
    print(f"{'':<16}{'v1 (LIKE)':>12}{'v2 (FULLTEXT)':>16}")
    print("-" * 44)
    for clave in izquierda:
        print(f"{clave:<16}{izquierda[clave]:>11.0%}{derecha[clave]:>16.0%}")

    print(f"\n{'caso':<10}{'categoría':<16}{'v1':>6}{'v2':>6}   recall v1 -> v2")
    print("-" * 60)
    por_caso = {r.case_code: r for r in v2.results}
    for anterior in v1.results:
        actual = por_caso[anterior.case_code]
        print(
            f"{anterior.case_code:<10}{anterior.category:<16}"
            f"{'sí' if anterior.passed else 'no':>6}{'sí' if actual.passed else 'no':>6}"
            f"   {anterior.retrieval_recall:.2f} -> {actual.retrieval_recall:.2f}"
        )
    print(f"\nCorridas: v1={v1.id}  v2={v2.id}")


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    if get_settings().app_env != "development":
        raise SystemExit("La comparación solo corre con APP_ENV=development")

    seed(reset=True)
    with SessionLocal() as db:
        conjunto = db.scalar(
            select(EvaluationSet).where(
                EvaluationSet.name == SET_NAME, EvaluationSet.version == SET_VERSION
            )
        )
        curadora = _curator(db)
        with legacy_retrieval():
            v1 = evaluation_service.run_evaluation(db, curadora, conjunto.id)
        v2 = evaluation_service.run_evaluation(db, curadora, conjunto.id)

    _print_comparison(v1, v2)


if __name__ == "__main__":
    main()
