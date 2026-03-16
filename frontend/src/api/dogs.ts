// src/api/dogs.ts
/**
 * API-клиент для модуля собак.
 *
 * Все запросы идут через Vite proxy:
 *   /api/* → http://localhost:8000/api/*
 *
 * Бэкенд endpoints:
 *   GET  /api/dogs/?q=...&sex=...  — список + поиск (DRF ViewSet)
 *   GET  /api/dogs/{id}/           — детали собаки
 *   GET  /api/dogs/{id}/pedigree/  — родословная
 *   GET  /api/dogs/stats/          — статистика
 */

import type {
  DogListItem,
  DogDetail,
  DogSearchParams,
  PaginatedResponse,
  PedigreeNode,
  DogStats,
} from "@/types/dog";

const API_BASE = "/api/dogs";

// ----------------------------------------------------------
// Утилита
// ----------------------------------------------------------

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// DRF возвращает { count, results, next, previous }
// Маппим в наш формат { data, meta }
interface DRFResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

function mapDRFResponse<T>(
  drf: DRFResponse<T>,
  page: number,
  perPage: number
): PaginatedResponse<T> {
  return {
    data: drf.results,
    meta: {
      total: drf.count,
      total_pages: Math.ceil(drf.count / perPage),
      page,
      per_page: perPage,
      has_more: drf.next !== null,
    },
  };
}

// ----------------------------------------------------------
// Поиск собак
// ----------------------------------------------------------

export async function searchDogs(
  params: DogSearchParams
): Promise<PaginatedResponse<DogListItem>> {
  const sp = new URLSearchParams();

  if (params.q)        sp.set("q",         params.q);
  if (params.sex)      sp.set("sex",        params.sex);
  if (params.color)    sp.set("color",      params.color);
  if (params.kennel)   sp.set("kennel",     params.kennel);
  if (params.country)  sp.set("country",    params.country);
  if (params.year_from) sp.set("year_from", params.year_from);
  if (params.year_to)  sp.set("year_to",    params.year_to);
  if (params.with_photo) sp.set("with_photo", params.with_photo);

  const page    = params.page     ?? 1;
  const perPage = params.per_page ?? 20;
  sp.set("page",     String(page));
  sp.set("per_page", String(perPage));

  const url = `${API_BASE}/?${sp.toString()}`;
  const drf = await fetchJson<DRFResponse<DogListItem>>(url);
  return mapDRFResponse(drf, page, perPage);
}

// ----------------------------------------------------------
// Список всех собак (с пагинацией)
// ----------------------------------------------------------

export async function getDogs(
  page = 1,
  perPage = 20
): Promise<PaginatedResponse<DogListItem>> {
  const drf = await fetchJson<DRFResponse<DogListItem>>(
    `${API_BASE}/?page=${page}&per_page=${perPage}`
  );
  return mapDRFResponse(drf, page, perPage);
}

// ----------------------------------------------------------
// Детали собаки
// ----------------------------------------------------------

export async function getDogDetail(id: number): Promise<DogDetail> {
  return fetchJson<DogDetail>(`${API_BASE}/${id}/`);
}

// ----------------------------------------------------------
// Родословная (рекурсивное дерево)
// ----------------------------------------------------------

export async function getDogPedigree(
  id: number,
  depth = 3
): Promise<PedigreeNode> {
  return fetchJson<PedigreeNode>(
    `${API_BASE}/${id}/pedigree/?generations=${depth}`
  );
}

// ----------------------------------------------------------
// Статистика
// ----------------------------------------------------------

export async function getDogStats(): Promise<DogStats> {
  return fetchJson<DogStats>(`${API_BASE}/stats/`);
}