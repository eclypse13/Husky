export interface SiteBannerSettings {
  is_enabled: boolean;
  message: string;
  updated_at: string | null;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function getSiteBanner(): Promise<SiteBannerSettings> {
  return fetchJson<SiteBannerSettings>("/api/site-banner/");
}

