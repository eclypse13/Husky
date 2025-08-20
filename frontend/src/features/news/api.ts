export async function getNews() {
    const res = await fetch("/mocks/db/news.json");
    return res.json();
}
