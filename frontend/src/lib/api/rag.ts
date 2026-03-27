import { api } from "./client";

export interface RAGResponse {
  id: number;
  user_id: number;
  query: string;
  response?: string;
  created_at: string;
}

export async function askRag(
  query: string,
  opts?: { budget_max?: number; occasion?: string; relationship?: string },
): Promise<RAGResponse> {
  return api.post<RAGResponse>("/rag/ask", { query, top_k: 5, ...opts }, true);
}
