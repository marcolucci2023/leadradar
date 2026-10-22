const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LeadResult {
  id?: string;
  name: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  instagram?: string;
  facebook?: string;
  ai_score?: number | null;
  ai_reason?: string;
  ai_message_subject?: string;
  ai_message_body?: string;
}

async function request(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function searchBusinesses(
  token: string,
  city: string,
  businessType: string,
  radius: number
) {
  return request("/api/v1/search/", {
    method: "POST",
    body: JSON.stringify({ city, business_type: businessType, radius }),
  });
}

export async function enrichAndScoreLead(
  token: string,
  name: string,
  address: string,
  website: string,
  businessType: string,
  city: string
) {
  return request("/api/v1/leads/enrich", {
    method: "POST",
    body: JSON.stringify({
      name,
      address,
      website,
      business_type: businessType,
      city,
    }),
  });
}

export async function sendLeadEmail(
  token: string,
  to: string,
  subject: string,
  body: string
) {
  return request("/api/v1/leads/send-email", {
    method: "POST",
    body: JSON.stringify({ to, subject, body }),
  });
}

export async function createCampaign(
  name: string,
  leadIds: string[],
  description = ""
) {
  return request("/api/v1/campaigns/", {
    method: "POST",
    body: JSON.stringify({ name, description, lead_ids: leadIds }),
  });
}

export async function listCampaigns() {
  return request("/api/v1/campaigns/");
}

export async function getCampaign(id: string) {
  return request(`/api/v1/campaigns/${id}`);
}

export async function updateCampaign(
  id: string,
  data: { name?: string; description?: string; status?: string }
) {
  return request(`/api/v1/campaigns/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function addLeadsToCampaign(id: string, leadIds: string[]) {
  return request(`/api/v1/campaigns/${id}/leads`, {
    method: "POST",
    body: JSON.stringify({ lead_ids: leadIds }),
  });
}

export async function removeLeadFromCampaign(id: string, leadId: string) {
  return request(`/api/v1/campaigns/${id}/leads/${leadId}`, {
    method: "DELETE",
  });
}