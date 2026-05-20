// src/types/dog.ts

export interface DogListItem {
  id: number;
  uuid: string;
  zoo_hash: string;
  display_name: string;
  registered_name: string;
  call_name: string | null;
  sex: number;
  sex_display: string;
  year_of_birth: number | null;
  date_of_birth: string | null;
  color: string | null;
  photo_url: string | null;
  dog_photo: string | null; // yandex disk photo
  land_of_birth: string | null;
  prefix_titles: string | null;
  suffix_titles: string | null;
  breeder_names: string[];
}

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
  dog_photo: string | null;
}

export interface DogTitle {
  id: number;
  short_name: string;
  long_name: string | null;
  is_prefix: boolean;
  country: string;
  winner_year: number | null;
}

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
  dog_photo: string | null;
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

export interface PedigreeNode {
  id: number;
  uuid: string;
  display_name: string;
  registered_name: string;
  call_name: string | null;
  sex: number;
  year_of_birth: number | null;
  date_of_birth: string | null;
  photo_url: string | null;
  dog_photo: string | null;
  color: string | null;
  land_of_birth: string | null;
  prefix_titles: string | null;
  suffix_titles: string | null;
  coi: number | null;
  dam: PedigreeNode | null;
  sire: PedigreeNode | null;
}

export interface DogStats {
  total: number;
  males: number;
  females: number;
  with_photo: number;
  breeders?: number;
  total_owners: number;
}

export interface CoiCalculationResult {
  coi: number;
  coi_updated_on: string;
  generations: number;
  common_ancestors: number;
  total_ancestors_sire: number;
  total_ancestors_dam: number;
  ancestor_contributions: Record<string, number>;
}