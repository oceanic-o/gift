import { api } from "./client";

export interface AdminStats {
  total_users: number;
  total_gifts: number;
  total_interactions: number;
  total_recommendations: number;
  popular_categories: { name: string; count: number }[];
  best_model?: {
    model_name: string;
    precision: number;
    recall: number;
    f1_score: number;
    accuracy: number;
    evaluated_at: string;
  };
  interaction_breakdown: Record<string, number>;
}

export interface ModelMetric {
  id: number;
  model_name: string;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  evaluated_at: string;
}

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

export interface AdminInteraction {
  id: number;
  user_id: number;
  gift_id: number;
  interaction_type: string;
  rating?: number;
  timestamp: string;
}

export interface AdminGift {
  id: number;
  title: string;
  description?: string;
  category_id: number;
  price: number;
  occasion?: string;
  relationship?: string;
  image_url?: string;
  product_url?: string;
  created_at: string;
  category?: { id: number; name: string };
}

export interface CategoryResponse {
  id: number;
  name: string;
}

export interface GiftCreatePayload {
  title: string;
  description?: string;
  category_id: number;
  price: number;
  occasion?: string;
  relationship?: string;
  image_url?: string;
  product_url?: string;
}

export interface TuningResult {
  content_weight: number;
  collaborative_weight: number;
  tfidf_weight: number;
  embed_weight: number;
  precision: number;
  recall: number;
  f1: number;
  accuracy: number;
}

export interface TuningResponse {
  results: TuningResult[];
  best?: TuningResult | null;
}

export interface EvaluateAllModelsResult {
  model_name: string;
  users_evaluated: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  f1_score: number | null;
  accuracy: number | null;
  error_rate: number | null;
  mae: number | null;
  rmse: number | null;
  coverage: number | null;
  precision_at_k: number | null;
  recall_at_k: number | null;
  f1_at_k: number | null;
  hit_rate_at_k: number | null;
  ndcg_at_k: number | null;
  map_at_k: number | null;
  mrr_at_k: number | null;
  validity_rate: number | null;
  invalidity_rate: number | null;
  avg_validity_score: number | null;
}

export interface EvaluateAllModelsResponse {
  message: string;
  mode: string;
  users_evaluated: number;
  results: EvaluateAllModelsResult[];
}

export interface DatasetMetadata {
  file_path: string;
  schema_version?: string | null;
  generator_version?: string | null;
  image_source?: string | null;
  image_license?: string | null;
  total_products: number;
  total_users?: number | null;
  categories: string[];
  occasions: string[];
  age_ranges: string[];
  product_fields: string[];
}

export interface TableColumn {
  name: string;
  type: string;
  nullable: boolean;
  default?: string | null;
}

export interface TableForeignKey {
  constrained_columns: string[];
  referred_table: string;
  referred_columns: string[];
}

export interface TableSchema {
  name: string;
  columns: TableColumn[];
  foreign_keys: TableForeignKey[];
}

export interface DatabaseSchema {
  tables: TableSchema[];
}

export interface AdminQueryRequest {
  sql: string;
  max_rows?: number;
}

export interface AdminQueryResponse {
  columns: string[];
  rows: Array<Array<string | number | boolean | null>>;
  row_count: number;
}

export const getStats = () => api.get<AdminStats>("/admin/stats", true);
export const getAllUsers = () => api.get<AdminUser[]>("/admin/users", true);
export const getAllMetrics = () =>
  api.get<ModelMetric[]>("/admin/metrics", true);
export const getAllInteractions = () =>
  api.get<AdminInteraction[]>("/admin/interactions", true);
export const retrainModel = () =>
  api.post<{ message: string }>("/admin/retrain", {}, true, {
    timeoutMs: 600000,
    retry: { attempts: 0 },
  });
export const evaluateModel = () =>
  api.post<EvaluateAllModelsResponse>("/admin/evaluate", {}, true, {
    timeoutMs: 600000,
    retry: { attempts: 0 },
  });

export const deleteUser = (userId: number) =>
  api.delete<{ message: string }>(`/admin/users/${userId}`, true);
export const updateUserRole = (userId: number, role: string) =>
  api.patch<AdminUser>(`/admin/users/${userId}/role`, { role }, true);
export const deleteInteraction = (interactionId: number) =>
  api.delete<{ message: string }>(`/admin/interactions/${interactionId}`, true);

export const importGifts = (limit?: number, force?: boolean) => {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (force) params.set("force", "true");
  const qs = params.toString() ? `?${params}` : "";
  return api.post<{ message: string; created: number; skipped: number }>(
    `/admin/gifts/import${qs}`,
    {},
    true,
  );
};

export const resetCatalog = (limit?: number, embedBatchSize?: number) => {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (embedBatchSize) params.set("embed_batch_size", String(embedBatchSize));
  const qs = params.toString() ? `?${params}` : "";
  return api.post<{ message: string; import: any; embeddings: any }>(
    `/admin/catalog/reset${qs}`,
    {},
    true,
  );
};

export const embedGifts = () =>
  api.post<{ message: string; updated?: number }>(
    "/admin/embeddings",
    {},
    true,
  );

export const ingestWebGifts = (query: string, limit?: number) => {
  const params = new URLSearchParams();
  params.set("query", query);
  if (limit) params.set("limit", String(limit));
  const qs = params.toString() ? `?${params}` : "";
  return api.post<{ message: string; created: number; skipped: number }>(
    `/admin/web-gifts/ingest${qs}`,
    {},
    true,
  );
};

export const getDatasetMetadata = () =>
  api.get<DatasetMetadata>("/admin/dataset/metadata", true);

export const getDatabaseSchema = () =>
  api.get<DatabaseSchema>("/admin/db/schema", true);

export const runAdminQuery = (payload: AdminQueryRequest) =>
  api.post<AdminQueryResponse>("/admin/db/query", payload, true);

export const listGifts = (limit = 50) =>
  api.get<AdminGift[]>(`/gifts/?limit=${limit}`, true);
export const createGift = (payload: GiftCreatePayload) =>
  api.post<AdminGift>("/gifts/", payload, true);
export const deleteGift = (giftId: number) =>
  api.delete(`/gifts/${giftId}`, true);
export const listCategories = () =>
  api.get<CategoryResponse[]>("/categories/", true);
export const createCategory = (name: string) =>
  api.post<CategoryResponse>("/categories/", { name }, true);
export async function tuneModels(): Promise<TuningResponse> {
  return api.post<TuningResponse>("/admin/tune", {}, true, {
    timeoutMs: 60000,
    retry: { attempts: 0 },
  });
}

export async function evaluateModelLong(): Promise<any> {
  return api.post<any>("/admin/evaluate", {}, true, { timeoutMs: 60000 });
}

export interface EnvSettingsResponse {
  backend: Record<string, string>;
  frontend: Record<string, string>;
}

export interface EnvSettingsUpdate {
  backend?: Record<string, string>;
  frontend?: Record<string, string>;
}

export const getEnvSettings = () =>
  api.get<EnvSettingsResponse>("/admin/settings", true, {
    timeoutMs: 30000,
    retry: { attempts: 1 },
  });
export const updateEnvSettings = (payload: EnvSettingsUpdate) =>
  api.patch<{ message: string }>("/admin/settings", payload, true, {
    timeoutMs: 30000,
    retry: { attempts: 0 },
  });
