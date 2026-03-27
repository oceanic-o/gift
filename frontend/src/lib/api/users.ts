import { api } from "./client";
import type { RecommendationWithGift } from "./recommendations";

export interface UserProfile {
  id: number;
  user_id: number;
  age?: string | null;
  gender?: string | null;
  hobbies?: string | null;
  relationship?: string | null;
  occasion?: string | null;
  budget_min?: number | null;
  budget_max?: number | null;
  favorite_categories?: string[] | null;
  occasions?: string[] | null;
  gifting_for_ages?: string[] | null;
  interests?: string[] | null;
  updated_at: string;
}

export interface UserProfileUpdate {
  age?: string | null;
  gender?: string | null;
  hobbies?: string | null;
  relationship?: string | null;
  occasion?: string | null;
  budget_min?: number | null;
  budget_max?: number | null;
  favorite_categories?: string[] | null;
  occasions?: string[] | null;
  gifting_for_ages?: string[] | null;
  interests?: string[] | null;
}

export type UserPreferencesUpdate = UserProfileUpdate;

export interface PasswordChangePayload {
  old_password: string;
  new_password: string;
  confirm_password: string;
}

export async function getProfile(): Promise<UserProfile | null> {
  return api.get<UserProfile | null>("/users/me/profile", true);
}

export async function updateProfile(
  payload: UserProfileUpdate,
): Promise<UserProfile> {
  return api.put<UserProfile>("/users/me/profile", payload, true);
}

export async function savePreferences(
  payload: UserPreferencesUpdate,
): Promise<UserProfile> {
  return api.post<UserProfile>("/users/me/preferences", payload, true);
}

export async function changePassword(
  payload: PasswordChangePayload,
): Promise<{ message: string }> {
  return api.post<{ message: string }>("/users/me/password", payload, true);
}

export async function getHomeRecommendations(): Promise<
  RecommendationWithGift[]
> {
  return api.get<RecommendationWithGift[]>("/users/me/home-recommendations", true, {
    timeoutMs: 45000,
    retry: { attempts: 1 },
  });
}

export interface PublicReview {
  name: string;
  role: string;
  avatar: string;
  rating: number;
  review: string;
  reviewed_at: string;
}

export async function getPublicReviews(limit = 6): Promise<PublicReview[]> {
  const qs = `?limit=${encodeURIComponent(String(limit))}`;
  return api.get<PublicReview[]>(`/users/public-reviews${qs}`, false, {
    timeoutMs: 15000,
    retry: { attempts: 1 },
  });
}
