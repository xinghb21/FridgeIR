import type {
  ParseResponse,
  RecipeDetail,
  RecipeEnhanceRequest,
  RecipeEnhanceResponse,
  SearchRequest,
  SearchResponse,
} from "./types";

// 默认空串：走同源相对路径 /api，由 Vite 代理转发到后端，避免 CORS。
// 设置 VITE_API_BASE_URL 可让前端直连指定后端地址。
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_BASE_URL + path, init);
  } catch {
    throw new Error("无法连接后端，请确认服务已启动（http://127.0.0.1:8000）");
  }
  if (!res.ok) {
    // FastAPI 错误体形如 {"detail": "..."}，优先把后端原因透传给用户。
    let detail = "";
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* 忽略非 JSON 错误体 */
    }
    if (res.status === 404) throw new Error(detail || "菜谱不存在");
    if (res.status === 422) throw new Error(detail || "搜索参数错误");
    if (res.status >= 500) throw new Error(detail || "服务异常，请稍后重试");
    throw new Error(detail || `请求失败（${res.status}）`);
  }
  return (await res.json()) as T;
}

export function searchByIngredients(req: SearchRequest): Promise<SearchResponse> {
  return request<SearchResponse>("/api/v1/search/by-ingredients", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export function getRecipe(recipeId: number): Promise<RecipeDetail> {
  return request<RecipeDetail>(`/api/v1/recipes/${recipeId}`);
}

export function parseIngredients(items: string[]): Promise<ParseResponse> {
  return request<ParseResponse>("/api/v1/ingredients/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
}

export function enhanceRecipe(
  recipeId: number,
  payload: RecipeEnhanceRequest
): Promise<RecipeEnhanceResponse> {
  return request<RecipeEnhanceResponse>(`/api/v1/recipes/${recipeId}/enhance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(API_BASE_URL + "/health");
    if (!res.ok) return false;
    const data = (await res.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  }
}
