import { api } from "./client";

export async function listHobbies(): Promise<string[]> {
  return api.get<string[]>(`/taxonomy/hobbies`);
}
export async function listAgeGroups(): Promise<string[]> {
  return api.get<string[]>(`/taxonomy/age-groups`);
}
export async function listRelationships(): Promise<string[]> {
  return api.get<string[]>(`/taxonomy/relationships`);
}
export async function listOccasions(): Promise<string[]> {
  return api.get<string[]>(`/taxonomy/occasions`);
}
export async function listGenders(): Promise<string[]> {
  return api.get<string[]>(`/taxonomy/genders`);
}
export async function listBudgets(): Promise<string[]> {
  return api.get<string[]>(`/taxonomy/budgets`);
}
export async function listAgeRules(): Promise<Record<string, string[]>> {
  return api.get<Record<string, string[]>>(`/taxonomy/age-rules`);
}
