export type RatingItem = {
    id: string;
    name: string;
    kennel?: string;
    points: number;
    category: "producers" | "litters" | "champioms" | "young";
    year: number;
};
