from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.tables import Ingredient, IngredientAlias
from app.services.normalizer import DEFAULT_ALIAS_MAP, NormalizedIngredient, normalize_ingredient

MAX_INGREDIENT_NAME_LENGTH = 80


def load_alias_map(db: Session) -> dict[str, str]:
    rows = db.execute(
        select(IngredientAlias.alias, Ingredient.canonical_name).join(Ingredient, Ingredient.id == IngredientAlias.ingredient_id)
    ).all()
    alias_map = DEFAULT_ALIAS_MAP.copy()
    alias_map.update({alias: canonical for alias, canonical in rows})
    return alias_map


def ensure_ingredient(db: Session, canonical_name: str, aliases: list[str] | None = None) -> Ingredient:
    ingredient = db.scalar(select(Ingredient).where(Ingredient.canonical_name == canonical_name))
    if ingredient is None:
        ingredient = Ingredient(canonical_name=canonical_name)
        db.add(ingredient)
        db.flush()

    alias_values = set(aliases or [])
    alias_values.add(canonical_name)
    for alias in alias_values:
        if not alias or len(alias) > MAX_INGREDIENT_NAME_LENGTH:
            continue
        # 真实数据量变大后，同一个事务里可能多次遇到相同 alias。
        # 直接使用 PostgreSQL 的冲突忽略，避免唯一约束错误中断整批导入。
        db.execute(
            insert(IngredientAlias)
            .values(ingredient_id=ingredient.id, alias=alias, source="auto", confidence=1.0)
            .on_conflict_do_nothing(index_elements=["alias"])
        )

    return ingredient


def seed_default_aliases(db: Session) -> int:
    created = 0
    aliases_by_canonical: dict[str, list[str]] = {}
    for alias, canonical in DEFAULT_ALIAS_MAP.items():
        aliases_by_canonical.setdefault(canonical, []).append(alias)

    for canonical, aliases in aliases_by_canonical.items():
        existing_aliases = {
            row[0]
            for row in db.execute(
                select(IngredientAlias.alias).where(IngredientAlias.alias.in_(set(aliases) | {canonical}))
            ).all()
        }
        ensure_ingredient(db, canonical, aliases=aliases)
        created += len((set(aliases) | {canonical}) - existing_aliases)
    return created


def normalize_with_db(db: Session, raw: str) -> NormalizedIngredient:
    return normalize_ingredient(raw, load_alias_map(db))
