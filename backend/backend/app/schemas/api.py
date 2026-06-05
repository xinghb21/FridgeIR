from typing import Any, Literal

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    items: list[str] = Field(default_factory=list)


class ParsedIngredient(BaseModel):
    raw: str
    canonical: str
    quantity: float | None = None
    unit: str | None = None
    confidence: float


class ParseResponse(BaseModel):
    ingredients: list[ParsedIngredient]
    excluded_ingredients: list[str]
    need_confirmation: list[str]


class SearchFilters(BaseModel):
    max_minutes: int | None = None
    difficulty_lte: int | None = None
    cuisine: list[str] | None = None
    spice: Literal["spicy", "not_spicy"] | None = None
    complexity: Literal["simple", "complex"] | None = None
    count_seasonings_as_ingredients: bool = False
    diet: Literal["meat", "vegetarian"] | None = None
    for_children: bool | None = None
    serving_size: Literal["large", "small"] | None = None
    seasoning_amount: Literal["many", "few"] | None = None
    methods: list[Literal["炒", "蒸", "煎", "拌", "炖", "炸"]] = Field(default_factory=list)


class SearchRequest(BaseModel):
    items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchItem(BaseModel):
    recipe_id: int
    source_recipe_id: str | None
    title: str
    dish: str | None = None
    quality_score: float
    matched: list[str]
    missing: list[str]
    bucket: str
    score: float
    reason: str
    recipe_tags: list[str] = Field(default_factory=list)
    preference_matches: list[str] = Field(default_factory=list)
    preference_mismatches: list[str] = Field(default_factory=list)
    preference_score: float = 0.0
    rerank_score: float | None = None
    rerank_reason: str | None = None


class SearchResponse(BaseModel):
    parsed: ParseResponse
    total: int
    items: list[SearchItem]
    facets: dict


class ImportRequest(BaseModel):
    path: str | None = None


class RecipeIngredientOut(BaseModel):
    raw_text: str
    canonical_name: str | None
    quantity: float | None = None
    unit: str | None = None
    required: bool
    position: int


class RecipeStepOut(BaseModel):
    step_no: int
    text: str


class RecipeDetail(BaseModel):
    recipe_id: int
    source_recipe_id: str | None
    title: str
    dish: str | None = None
    description: str | None = None
    quality_score: float
    recipe_tags: list[str] = Field(default_factory=list)
    ingredients: list[RecipeIngredientOut]
    steps: list[RecipeStepOut]


class RecipeEnhanceRequest(BaseModel):
    user_items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    preferences: SearchFilters = Field(default_factory=SearchFilters)


class RecipeEnhanceResponse(BaseModel):
    recipe_id: int
    source_recipe_id: str | None
    original_title: str
    generated_title: str
    summary: str
    bucket: str
    bucket_reason: str
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    ingredients: list[str]
    steps: list[str]
    tips: list[str] = Field(default_factory=list)
    model: str
    disclaimer: str


class FullFlowInput(BaseModel):
    items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=5, ge=1, le=20)


class DemoFullFlowRequest(BaseModel):
    items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=5, ge=1, le=20)


class FullFlowItem(BaseModel):
    rank: int
    search_result: SearchItem
    generated_recipe: RecipeEnhanceResponse | None = None
    generation_error: str | None = None


class DemoFullFlowResponse(BaseModel):
    input: FullFlowInput
    rerank_status: dict[str, Any] | None = None
    search_total: int
    items: list[FullFlowItem]
    cache_hit: bool
    case_id: str
    strict_rerank_hit: bool
    cache_note: str
