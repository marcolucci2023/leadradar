const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Erreur ${res.status}`);
  }
  return res.json();
}

export async function register(email: string, password: string, fullName: string) {
  return request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export async function login(email: string, password: string) {
  return request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export interface LeadResult {
  name: string;
  address: string;
  phone?: string;
  website?: string;
  email?: string;
  instagram?: string;
  facebook?: string;
  lat?: number;
  lon?: number;
  business_type?: string;
  opening_hours?: string;
  description?: string;
  google_maps?: string;
  ai_score?: number | null;
  ai_reason?: string;
  ai_message_subject?: string;
  ai_message_body?: string;
}

export interface SearchResponse {
  results: LeadResult[];
  total: number;
  source?: string;
}

export async function searchBusinesses(
  token: string, city: string, businessType: string, radius: number
): Promise<SearchResponse> {
  return request("/api/v1/search/", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ city, business_type: businessType, radius }),
  });
}

export async function enrichAndScoreLead(
  token: string, name: string, address: string,
  website: string, businessType: string, city: string,
  phone: string = "", email: string = "",
  facebook: string = "", instagram: string = ""
) {
  return request("/api/v1/leads/full-pipeline?language=fr", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      name, address, website,
      business_type: businessType,
      city,
    }),
  });
}
export async function sendLeadEmail(
  token: string,
  toEmail: string,
  subject: string,
  body: string
): Promise<{ status: string; id: string }> {
  const res = await fetch(`${API_URL}/api/v1/leads/send-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ to_email: toEmail, subject, body }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur ${res.status}`);
  }
  return res.json();
}
