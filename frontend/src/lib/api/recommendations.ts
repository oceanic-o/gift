import { api, type RequestOptions } from "./client";

export type InteractionType = "click" | "rating" | "purchase";

export interface RecommendationWithGift {
  gift_id: number;
  score: number;
  model_type: string;
  title: string;
  description?: string;
  price: number;
  occasion?: string;
  relationship?: string;
  image_url?: string;
  product_url?: string;
  category_name?: string;
  is_valid_recommendation?: boolean | null;
  validity_score?: number | null;
  validity_reasons?: string[] | null;
  query_cosine_similarity?: number | null;
  content_cosine_similarity?: number | null;
  collaborative_cosine_similarity?: number | null;
  knowledge_similarity?: number | null;
  rag_similarity?: number | null;
  occasion_match?: boolean | null;
  relationship_match?: boolean | null;
  age_match?: boolean | null;
  gender_match?: boolean | null;
  price_match?: boolean | null;
  hobby_overlap?: number | null;
}

export type MetricValue =
  | number
  | string
  | boolean
  | null
  | undefined
  | MetricValue[]
  | { [key: string]: MetricValue };

export interface ModelResult {
  model: "content" | "collaborative" | "hybrid" | "knowledge" | "rag";
  label: string;
  gifts: RecommendationWithGift[];
  is_cold_start: boolean;
  metrics: Record<string, MetricValue>;
  explanation?: string;
}

export interface CompareResponse {
  user_has_history: boolean;
  models: ModelResult[];
}

export interface RecFilters {
  top_n?: number;
  occasion?: string;
  relationship?: string;
  min_price?: number;
  max_price?: number;
  query?: string;
  age?: string;
  gender?: string;
  hobbies?: string;
}

export async function getRecommendations(
  f?: RecFilters,
  options?: RequestOptions,
): Promise<RecommendationWithGift[]> {
  const p = new URLSearchParams();
  if (f?.top_n != null) p.set("top_n", String(f.top_n));
  if (f?.occasion) p.set("occasion", f.occasion);
  if (f?.relationship) p.set("relationship", f.relationship);
  if (f?.min_price != null) p.set("min_price", String(f.min_price));
  if (f?.max_price != null) p.set("max_price", String(f.max_price));
  if (f?.query) p.set("query", f.query);
  if (f?.age) p.set("age", f.age);
  if (f?.gender) p.set("gender", f.gender);
  if (f?.hobbies) p.set("hobbies", f.hobbies);
  const qs = p.toString() ? `?${p}` : "";
  return api.get<RecommendationWithGift[]>(`/recommendations${qs}`, true, {
    timeoutMs: 25000,
    retry: { attempts: 2 },
    ...(options || {}),
  });
}

export async function compareModels(
  f?: RecFilters,
  options?: RequestOptions,
): Promise<CompareResponse> {
  const p = new URLSearchParams();
  if (f?.top_n != null) p.set("top_n", String(f.top_n));
  if (f?.occasion) p.set("occasion", f.occasion);
  if (f?.relationship) p.set("relationship", f.relationship);
  if (f?.min_price != null) p.set("min_price", String(f.min_price));
  if (f?.max_price != null) p.set("max_price", String(f.max_price));
  if (f?.query) p.set("query", f.query);
  if (f?.age) p.set("age", f.age);
  if (f?.gender) p.set("gender", f.gender);
  if (f?.hobbies) p.set("hobbies", f.hobbies);
  const qs = p.toString() ? `?${p}` : "";
  return api.get<CompareResponse>(`/recommendations/compare${qs}`, true, {
    timeoutMs: 30000,
    retry: { attempts: 2 },
    ...(options || {}),
  });
}

export async function recordInteraction(
  gift_id: number,
  interaction_type: InteractionType,
  rating?: number,
): Promise<void> {
  await api.post("/interactions", { gift_id, interaction_type, rating }, true);
}

// ── New: minimal image-only recommendations ─────────────────────────────────
export interface MinimalRecommendation {
  gift_id: number;
  image_url?: string;
  score: number;
  rank: number;
}

export async function getMinimalRecommendations(
  f?: RecFilters,
): Promise<MinimalRecommendation[]> {
  const p = new URLSearchParams();
  if (f?.top_n != null) p.set("top_n", String(f.top_n));
  if (f?.occasion) p.set("occasion", f.occasion);
  if (f?.relationship) p.set("relationship", f.relationship);
  if (f?.min_price != null) p.set("min_price", String(f.min_price));
  if (f?.max_price != null) p.set("max_price", String(f.max_price));
  if (f?.age) p.set("age", f.age);
  if (f?.gender) p.set("gender", f.gender);
  if (f?.hobbies) p.set("hobbies", f.hobbies);
  const qs = p.toString() ? `?${p}` : "";
  return api.get<MinimalRecommendation[]>(
    `/recommendations/minimal${qs}`,
    true,
  );
}

// ── New: per-gift details with metrics ─────────────────────────────────────
export interface CategoryResponse {
  id: number;
  name: string;
}
export interface GiftResponse {
  id: number;
  title: string;
  description?: string | null;
  category_id: number;
  price: number;
  occasion?: string | null;
  relationship?: string | null;
  age_group?: string | null;
  tags?: string | null;
  image_url?: string | null;
  product_url?: string | null;
  created_at: string;
  category?: CategoryResponse | null;
}

export interface GiftMetrics {
  hybrid_score: number;
  content_score: number;
  collab_score: number;
  knowledge_score?: number | null;
  confidence: number;
  occasion_match?: boolean | null;
  relationship_match?: boolean | null;
  age_group_match?: boolean | null;
  price_fit?: boolean | null;
  hobby_overlap?: number | null;
  tags_matched?: string[] | null;
  model_precision?: number | null;
  model_recall?: number | null;
  model_f1?: number | null;
  model_accuracy?: number | null;
  model_error_rate?: number | null;
  model_mae?: number | null;
  model_rmse?: number | null;
  model_coverage?: number | null;
  model_confusion_matrix?: number[][] | null;
  model_tp?: number | null;
  model_fp?: number | null;
  model_tn?: number | null;
  model_fn?: number | null;
  model_metrics_mode?: string | null;
}

export interface GiftDetailsWithMetrics {
  gift: GiftResponse;
  metrics: GiftMetrics;
}

// ── New: public model evaluation metrics history ───────────────────────────
export interface PublicModelMetric {
  id: number;
  model_name: string;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  evaluated_at: string;
}

export async function getPublicModelMetrics(
  limit = 50,
  options?: RequestOptions,
): Promise<PublicModelMetric[]> {
  const qs = `?limit=${encodeURIComponent(String(limit))}`;
  return api.get<PublicModelMetric[]>(`/recommendations/metrics${qs}`, true, {
    timeoutMs: 25000,
    retry: { attempts: 1 },
    ...(options || {}),
  });
}

export async function getGiftDetails(
  gift_id: number,
  f?: RecFilters,
  options?: RequestOptions,
): Promise<GiftDetailsWithMetrics> {
  const p = new URLSearchParams();
  if (f?.occasion) p.set("occasion", f.occasion);
  if (f?.relationship) p.set("relationship", f.relationship);
  if (f?.min_price != null) p.set("min_price", String(f.min_price));
  if (f?.max_price != null) p.set("max_price", String(f.max_price));
  if (f?.age) p.set("age", f.age);
  if (f?.gender) p.set("gender", f.gender);
  if (f?.hobbies) p.set("hobbies", f.hobbies);
  const qs = p.toString() ? `?${p}` : "";
  return api.get<GiftDetailsWithMetrics>(
    `/recommendations/${gift_id}/details${qs}`,
    true,
    { timeoutMs: 60000, retry: { attempts: 1 }, ...(options || {}) },
  );
}
