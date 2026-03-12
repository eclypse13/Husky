// src/types/dog.ts
/**
 * Типы данных для модуля собак.
 * Соответствуют сериализаторам Django: DogListSerializer, DogDetailSerializer, PedigreeSerializer
 */

// Ответ API /api/dogs/search/ и /api/dogs/
export interface DogListItem {
  id: number;
  uuid: string;
  zoo_hash: string;
  display_name: string;
  registered_name: string;
  call_name: string | null;
  sex: number;           // 1 = кобель, 2 = сука
  sex_display: string;   // "Кобель" / "Сука"
  year_of_birth: number | null;
  date_of_birth: string | null;
  color: string | null;
  photo_url: string | null;
  land_of_birth: string | null;
  prefix_titles: string | null;
  suffix_titles: string | null;
  breeder_names: string[];    // из breeder.name через dogbreederlink
}

// Пагинация
export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
    has_more: boolean;
  };
}

// Параметры поиска
export interface DogSearchParams {
  q?: string;
  sex?: string;
  color?: string;
  kennel?: string;
  country?: string;
  year_from?: string;
  year_to?: string;
  with_photo?: string;
  page?: number;
  per_page?: number;
}

// Родитель (краткий)
export interface DogParent {
  id: number;
  uuid: string;
  display_name: string;
  registered_name: string;
  sex: number;
  sex_display: string;
  year_of_birth: number | null;
  color: string | null;
  photo_url: string | null;
}

// Титул
export interface DogTitle {
  id: number;
  short_name: string;
  long_name: string | null;
  is_prefix: boolean;
  country: string;
  winner_year: number | null;
}

// Полная информация о собаке
export interface DogDetail {
  id: number;
  uuid: string;
  zoo_hash: string;
  zooportal_id: string | null;
  display_name: string;
  registered_name: string;
  call_name: string | null;
  link_name: string | null;
  sex: number;
  sex_display: string;
  year_of_birth: number | null;
  date_of_birth: string | null;
  color: string | null;
  size: string | null;
  weight: string | null;
  coi: number | null;
  coi_updated_on: string | null;
  photo_url: string | null;
  kennel: string | null;
  land_of_birth: string | null;
  registration_number: string | null;
  brand_chip: string | null;
  prefix_titles: string | null;
  suffix_titles: string | null;
  dam: DogParent | null;
  sire: DogParent | null;
  breeders: { id: number; name: string; kennel: string | null }[];
  owners: { id: number; name: string; kennel: string | null }[];
  titles: DogTitle[];
}

// Рекурсивная родословная
export interface PedigreeNode {
  id: number;
  uuid: string;
  display_name: string;
  registered_name: string;
  call_name: string | null;
  sex: number;
  year_of_birth: number | null;
  photo_url: string | null;
  color: string | null;
  dam: PedigreeNode | null;
  sire: PedigreeNode | null;
}

// Статистика
export interface DogStats {
  total: number;
  males: number;
  females: number;
  with_photo: number;
  breeders?: number;
  total_owners: number;
}

// Результат расчёта COI (POST /api/dogs/{id}/calculate_coi/)
export interface CoiCalculationResult {
  coi:                    number;
  coi_updated_on:         string;
  generations:            number;
  common_ancestors:       number;
  total_ancestors_sire:   number;
  total_ancestors_dam:    number;
  // {ancestor_id: вклад_в_%}
  ancestor_contributions: Record<string, number>;
}