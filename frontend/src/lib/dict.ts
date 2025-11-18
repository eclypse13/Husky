export type DictItem = {
  id: string;
  key: string;
  value: unknown;
  page?: string;
  locale?: string;
  updated_by?: string | null;
  updated_at?: string;
};

let dictPromise: Promise<DictItem[]> | null = null;
let dictCache: DictItem[] | null = null;
let fetchedAt = 0;
const TTL_MS = 5 * 60 * 1000; // 5 minutes

export async function getDict(options?: { force?: boolean }): Promise<DictItem[]> {
  const now = Date.now();
  if (!options?.force && dictCache && now - fetchedAt < TTL_MS) {
    return dictCache;
  }
  if (dictPromise) return dictPromise;

  dictPromise = (async () => {
    const doFetch = async () => {
      const res = await fetch('/api/dict/');
      if (res.status === 429) {
        // Simple backoff for rate limit
        await new Promise((r) => setTimeout(r, 1000));
        const retry = await fetch('/api/dict/');
        if (!retry.ok) throw new Error(`dict fetch failed ${retry.status}`);
        return retry.json();
      }
      if (!res.ok) throw new Error(`dict fetch failed ${res.status}`);
      return res.json();
    };

    const data = await doFetch();
    dictCache = Array.isArray(data) ? (data as DictItem[]) : [];
    fetchedAt = Date.now();
    return dictCache;
  })()
    .catch((e) => {
      dictPromise = null;
      throw e;
    });

  return dictPromise;
}

export function pickValue(dict: DictItem[], key: string, locale = 'ru'): string | null {
  const item = dict.find((x) => x?.key === key && (x?.locale === locale || !x?.locale));
  return item && item.value != null ? String(item.value) : null;
}

