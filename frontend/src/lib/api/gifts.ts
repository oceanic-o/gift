import { api } from "./client";

export interface Category {
  id: number;
  name: string;
}

export interface Gift {
  id: number;
  title: string;
  description?: string;
  category_id: number;
  category?: Category;
  price: number;
  occasion?: string;
  relationship?: string;
  image_url?: string;
  product_url?: string;
  created_at: string;
}

export interface GiftFilters {
  occasion?: string;
  relationship?: string;
  min_price?: number;
  max_price?: number;
  category_id?: number;
  skip?: number;
  limit?: number;
}

export interface CreateGiftPayload {
  title: string;
  description?: string;
  category_id: number;
  price: number;
  occasion?: string;
  relationship?: string;
  image_url?: string;
  product_url?: string;
}

function buildQS(filters?: GiftFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  if (filters.occasion) p.set("occasion", filters.occasion);
  if (filters.relationship) p.set("relationship", filters.relationship);
  if (filters.min_price != null) p.set("min_price", String(filters.min_price));
  if (filters.max_price != null) p.set("max_price", String(filters.max_price));
  if (filters.category_id != null)
    p.set("category_id", String(filters.category_id));
  if (filters.skip != null) p.set("skip", String(filters.skip));
  if (filters.limit != null) p.set("limit", String(filters.limit));
  return p.toString() ? `?${p}` : "";
}

export const listGifts = (f?: GiftFilters) =>
  api.get<Gift[]>(`/gifts/${buildQS(f)}`);
export const getGift = (id: number) => api.get<Gift>(`/gifts/${id}`);
export const createGift = (p: CreateGiftPayload) =>
  api.post<Gift>("/gifts/", p, true);
export const updateGift = (id: number, p: Partial<CreateGiftPayload>) =>
  api.put<Gift>(`/gifts/${id}`, p, true);
export const deleteGift = (id: number) =>
  api.delete<void>(`/gifts/${id}`, true);

export const listCategories = () => api.get<Category[]>("/categories/");
export const createCategory = (name: string) =>
  api.post<Category>("/categories/", { name }, true);
