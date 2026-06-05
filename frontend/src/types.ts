// 与后端接口文档一一对应的类型定义。

export interface ParsedIngredient {
  raw: string;
  canonical: string;
  quantity: number | null;
  unit: string | null;
  confidence: number;
}

export interface ParseResponse {
  ingredients: ParsedIngredient[];
  excluded_ingredients: string[];
  need_confirmation: string[];
}

export type Spice = "spicy" | "not_spicy";
export type Complexity = "simple" | "complex";
export type Diet = "meat" | "vegetarian";
export type ServingSize = "large" | "small";
export type SeasoningAmount = "many" | "few";
export type CookMethod = "炒" | "蒸" | "煎" | "拌" | "炖" | "炸";

export interface Filters {
  spice?: Spice | null;
  complexity?: Complexity | null;
  count_seasonings_as_ingredients?: boolean;
  diet?: Diet | null;
  for_children?: boolean | null;
  serving_size?: ServingSize | null;
  seasoning_amount?: SeasoningAmount | null;
  methods?: CookMethod[];
  max_minutes?: number | null;
  difficulty_lte?: number | null;
  cuisine?: string[] | null;
}

export interface SearchRequest {
  items?: string[];
  excluded_items?: string[];
  filters?: Filters;
  page?: number;
  page_size?: number;
}

export interface SearchItem {
  recipe_id: number;
  source_recipe_id: string | null;
  title: string;
  dish: string | null;
  quality_score: number;
  matched: string[];
  missing: string[];
  bucket: string;
  score: number;
  reason: string;
  recipe_tags: string[];
  preference_matches: string[];
  preference_mismatches: string[];
  preference_score: number;
  rerank_score?: number | null;
  rerank_reason?: string | null;
}

export interface Facet {
  name: string;
  count: number;
}

export interface SearchResponse {
  parsed: ParseResponse;
  total: number;
  items: SearchItem[];
  facets: {
    bucket?: Facet[];
    [key: string]: unknown;
  };
}

export interface RecipeIngredient {
  raw_text: string;
  canonical_name: string | null;
  quantity: number | null;
  unit: string | null;
  required: boolean;
  position: number;
}

export interface RecipeStep {
  step_no: number;
  text: string;
}

export interface RecipeDetail {
  recipe_id: number;
  source_recipe_id: string | null;
  title: string;
  dish: string | null;
  description: string | null;
  quality_score: number;
  recipe_tags: string[];
  ingredients: RecipeIngredient[];
  steps: RecipeStep[];
}

// AI 改良做法（POST /api/v1/recipes/{id}/enhance，走 DeepSeek）
export interface RecipeEnhanceRequest {
  user_items: string[];
  excluded_items: string[];
  preferences: Filters;
}

export interface RecipeEnhanceResponse {
  recipe_id: number;
  source_recipe_id: string | null;
  original_title: string;
  generated_title: string;
  summary: string;
  bucket: string;
  bucket_reason: string;
  matched: string[];
  missing: string[];
  ingredients: string[];
  steps: string[];
  tips: string[];
  model: string;
  disclaimer: string;
}
