import { apiFetch } from "@/lib/auth";
import type {
    PuppyFilters,
    PuppyListing,
    PuppyListResponse,
} from "@/types/puppy";

const BASE = "/api/puppies";

export async function fetchPuppies(filters: PuppyFilters = {}): Promise<PuppyListResponse> {
    const sp = new URLSearchParams();
    if (filters.q) sp.set("q", filters.q);
    if (filters.sex) sp.set("sex", filters.sex);
    if (filters.status) sp.set("status", filters.status);
    if (filters.nkp) sp.set("nkp", "1");
    if (filters.page) sp.set("page", String(filters.page));

    const res = await apiFetch(`${BASE}/?${sp.toString()}`);
    if (!res.ok) throw new Error(`Ошибка загрузки (${res.status})`);
    return res.json();
}

export async function fetchPuppy(id: number | string): Promise<PuppyListing> {
    const res = await apiFetch(`${BASE}/${id}/`);
    if (!res.ok) throw new Error(`Объявление не найдено (${res.status})`);
    return res.json();
}

/**
 * Создать/обновить объявление. Данные передаём как multipart,
 * т.к. вместе с полями отправляются фотографии (несколько файлов).
 */
export async function savePuppy(
    form: FormData,
    id?: number | string
): Promise<PuppyListing> {
    const url = id ? `${BASE}/${id}/` : `${BASE}/`;
    const method = id ? "PATCH" : "POST";
    const res = await apiFetch(url, { method, body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const msg =
            (data && data.error) ||
            (data && typeof data === "object"
                ? Object.entries(data)
                      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
                      .join("; ")
                : "") ||
            "Не удалось сохранить объявление";
        throw new Error(msg);
    }
    return data as PuppyListing;
}

export async function deletePuppy(id: number | string): Promise<void> {
    const res = await apiFetch(`${BASE}/${id}/`, { method: "DELETE" });
    if (!res.ok && res.status !== 204) throw new Error(`Не удалось удалить (${res.status})`);
}
