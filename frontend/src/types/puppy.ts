export interface PuppyPhoto {
    id: number;
    image: string | null;
    order: number;
}

export type PuppyStatus = "available" | "reserved" | "sold";

export interface PuppyListing {
    id: number;
    name: string;
    sex: "" | "male" | "female";
    sex_display: string;
    description: string;
    date_of_birth: string | null;
    color: string;
    city: string;
    price: string | null;
    kennel_name: string;
    kennel_url: string;
    breeder_contact: string;
    sire_archive_id: number | null;
    sire_name: string;
    dam_archive_id: number | null;
    dam_name: string;
    is_nkp_member: boolean;
    status: PuppyStatus;
    status_display: string;
    is_published: boolean;
    photos: PuppyPhoto[];
    owner: number;
    owner_name: string;
    can_edit: boolean;
    created_at: string;
    updated_at: string;
}

export interface PuppyListResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: PuppyListing[];
}

export interface PuppyFilters {
    q?: string;
    sex?: string;
    status?: string;
    nkp?: boolean;
    page?: number;
}
