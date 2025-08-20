export async function getRating(year?: number) {
    const res = await fetch("mocks/db/rating.json");
    const data = await res.json();
    return year ? data.filter((x: any) => x.year === year) : data;
}
