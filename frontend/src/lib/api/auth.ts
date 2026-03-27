import { api, setToken } from "./client";

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}
export interface LoginPayload {
  email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  name: string;
  email: string;
  role: "user" | "admin";
  created_at: string;
  provider?: string | null;
  google_sub?: string | null;
  avatar_url?: string | null;
  given_name?: string | null;
  family_name?: string | null;
  locale?: string | null;
}
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface GoogleLoginPayload {
  token: string;
}

export async function register(p: RegisterPayload): Promise<UserResponse> {
  return api.post<UserResponse>("/auth/register", p);
}

export async function login(p: LoginPayload): Promise<LoginResponse> {
  const data = await api.post<LoginResponse>("/auth/login", p);
  setToken(data.access_token);
  return data;
}

export async function googleLogin(
  p: GoogleLoginPayload,
): Promise<LoginResponse> {
  const data = await api.post<LoginResponse>("/auth/google", p);
  setToken(data.access_token);
  return data;
}
