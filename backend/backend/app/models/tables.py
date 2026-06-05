from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Ingredient(Base):
    """规范食材词典，例如 番茄、鸡蛋。"""

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(80))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("ingredients.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    aliases: Mapped[list["IngredientAlias"]] = relationship(back_populates="ingredient")


class IngredientAlias(Base):
    """食材别名到规范名的映射，例如 西红柿 -> 番茄。"""

    __tablename__ = "ingredient_aliases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)

    ingredient: Mapped[Ingredient] = relationship(back_populates="aliases")


class Recipe(Base):
    """来自 xiachufang 或未来数据源的规范化菜谱元信息。"""

    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("source_name", "source_recipe_id", name="uq_recipes_source"),
        Index("idx_recipes_filter", "rights_status", "takedown_status", "cuisine", "difficulty", "total_minutes"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_recipe_id: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    dish: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    cuisine: Mapped[str | None] = mapped_column(String(80))
    difficulty: Mapped[int | None] = mapped_column(SmallInteger)
    total_minutes: Mapped[int | None] = mapped_column(Integer)
    servings: Mapped[float | None] = mapped_column(Numeric(8, 2))
    quality_score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    rights_status: Mapped[str] = mapped_column(String(20), nullable=False, default="clear")
    takedown_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    content_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeIngredient.position"
    )
    steps: Mapped[list["RecipeStep"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeStep.step_no"
    )


class RecipeIngredient(Base):
    """属于某一道菜谱的食材明细行。

    raw_text 保留来源原文；canonical_name/ingredient_id 是搜索使用的规范化字段。
    """

    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        Index("idx_recipe_ingredients_recipe", "recipe_id"),
        Index("idx_recipe_ingredients_ingredient", "ingredient_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    ingredient_id: Mapped[int | None] = mapped_column(ForeignKey("ingredients.id"))
    raw_text: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_name: Mapped[str | None] = mapped_column(String(80))
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[str | None] = mapped_column(String(30))
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient | None] = relationship()


class RecipeStep(Base):
    """供菜谱详情页使用的有序烹饪步骤。"""

    __tablename__ = "recipe_steps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)

    recipe: Mapped[Recipe] = relationship(back_populates="steps")


class SourceRecord(Base):
    """原始导入负载快照，用于审计和可重复导入。"""

    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("source_name", "source_id", name="uq_source_records_source"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(64))
    imported_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SearchEvent(Base):
    """轻量搜索日志，后续用于指标统计和黄金查询集分析。"""

    __tablename__ = "search_events"
    __table_args__ = (
        CheckConstraint("result_count >= 0", name="ck_search_events_result_count_nonnegative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    query_text: Mapped[str | None] = mapped_column(Text)
    parsed_ingredients: Mapped[dict | None] = mapped_column(JSONB)
    filters: Mapped[dict | None] = mapped_column(JSONB)
    result_count: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
