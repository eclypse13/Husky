import {useState, useCallback, useRef} from "react";
import {Link} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import "./Breeding.css";
import type {DogListItem} from "@/types/dog";
import {DogAvatar} from "@/components/DogAvatar/DogAvatar";

interface DiseaseRisk {
    risk: number;
    level: "low" | "medium" | "high";
    basis: "ml" | "rules" | "genetics";
}

interface CoiInfo {
    level: "critical" | "high" | "medium" | "low" | "minimal" | "zero" | "unknown";
    title: string;
    text: string;
}

interface BreedingResult {
    hip_dysplasia: DiseaseRisk;
    eye_disease: DiseaseRisk;
    confidence: "low" | "medium" | "high";
    recommendation: "recommended" | "caution" | "not_recommended";
    model_used: string;
    features_used: string[];
    top_risks: { disease: string; risk: number; level: string; basis: string }[];
    offspring_coi: number | null;
    coi_info: CoiInfo | null;
}

const VERDICT = {
    recommended: {emoji: "✅", title: "Вязка рекомендована", sub: "Риски для потомства в пределах нормы"},
    caution: {emoji: "⚠️", title: "Требует осторожности", sub: "Обнаружены повышенные риски"},
    not_recommended: {emoji: "🚫", title: "Вязка не рекомендована", sub: "Высокий риск наследственных заболеваний"},
};

const CONFIDENCE_LABELS = {low: "Низкая", medium: "Средняя", high: "Высокая"};
const BASIS_LABELS = {ml: "ML модель", rules: "Правила OFA", genetics: "Генетика"};

const ML_DISEASES: Record<string, string> = {
    hip_dysplasia: "Дисплазия бёдер",
    eye_disease: "Болезни глаз",
};

const COI_COLORS: Record<string, string> = {
    critical: "var(--accent-red)",
    high: "var(--accent-orange)",
    medium: "var(--accent-orange)",
    low: "var(--bright-blue)",
    minimal: "var(--bright-blue)",
    zero: "var(--bright-blue)",
    unknown: "var(--text-light)",
};

function riskPct(r: number) {
    return `${(r * 100).toFixed(1)}%`;
}

function formatMeta(dog: DogListItem) {
    const p: (string | number)[] = [];
    if (dog.sex_display) p.push(dog.sex_display);
    if (dog.year_of_birth) p.push(dog.year_of_birth);
    return p.join(" · ");
}

interface SelectorProps {
    sex: 1 | 2;
    selected: DogListItem | null;
    onSelect: (d: DogListItem) => void;
    onClear: () => void;
}

function DogSelector({sex, selected, onSelect, onClear}: SelectorProps) {
    const [query, setQuery] = useState("");
    const [open, setOpen] = useState(false);
    const timer = useRef<ReturnType<typeof setTimeout>>();

    const {data, isFetching} = useQuery<{ count: number; results: DogListItem[] }>({
        queryKey: ["breed-search", sex, query],
        queryFn: () => fetch(`/api/dogs/?sex=${sex}&q=${encodeURIComponent(query)}&per_page=8`).then(r => r.json()),
        enabled: query.length >= 2,
        staleTime: 10_000,
    });

    const pick = useCallback((dog: DogListItem) => {
        onSelect(dog);
        setQuery("");
        setOpen(false);
    }, [onSelect]);

    return (
        <div className="breeding-selector-card">
            <div className="breeding-selector-label">
                <span className="breeding-selector-label-dot"/>
                {sex === 1 ? "♂ Кобель (Sire)" : "♀ Сука (Dam)"}
            </div>

            {selected ? (
                <div className="breeding-selected">
                    <DogAvatar
                        dog_photo={selected.dog_photo}
                        photo_url={selected.photo_url}
                        alt={selected.registered_name}
                        className="breeding-selected-photo"
                        loading="eager"
                    />
                    <div className="breeding-selected-info">
                        <Link to={`/archive/dog/${selected.id}`} className="breeding-selected-name">
                            {selected.registered_name} ↗
                        </Link>
                        {/*<div className="breeding-selected-meta">{formatMeta(selected)}</div>*/}
                    </div>
                    <button className="breeding-selected-clear" onClick={onClear} title="Убрать">✕</button>
                </div>
            ) : (
                <div className="breeding-search-wrap">
                    <span className="breeding-search-icon">🔍</span>
                    <input
                        className="breeding-search-input"
                        placeholder={`Поиск ${sex === 1 ? "кобеля" : "суки"} по имени…`}
                        value={query}
                        onChange={e => {
                            setQuery(e.target.value);
                            clearTimeout(timer.current);
                            timer.current = setTimeout(() => setOpen(e.target.value.length >= 2), 200);
                        }}
                        onFocus={() => query.length >= 2 && setOpen(true)}
                        onBlur={() => setTimeout(() => setOpen(false), 150)}
                        autoComplete="off"
                    />
                    {open && (
                        <div className="breeding-dropdown">
                            {isFetching && <div className="breeding-dropdown-empty">Поиск…</div>}
                            {!isFetching && !data?.results?.length &&
                                <div className="breeding-dropdown-empty">Ничего не найдено</div>}
                            {!isFetching && data?.results?.map(dog => (
                                <div key={dog.id} className="breeding-dropdown-item" onMouseDown={() => pick(dog)}>
                                    <DogAvatar
                                        dog_photo={dog.dog_photo}
                                        photo_url={dog.photo_url}
                                        alt={dog.registered_name}
                                        wrapClassName="breeding-dropdown-avatar"
                                    />
                                    <div>
                                        <div className="breeding-dropdown-name">{dog.registered_name}</div>
                                        <div className="breeding-dropdown-meta">{formatMeta(dog)}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function DiseaseCard({name, data}: { name: string; data: DiseaseRisk }) {
    const pct = data.risk * 100;
    const bar = Math.min(pct * 2, 100);
    return (
        <div className={`breeding-disease-card breeding-disease-card--${data.level}`}>
            <div className="breeding-disease-head">
                <div className="breeding-disease-name">{name}</div>
            </div>
            <div className="breeding-disease-bar-wrap">
                <div className="breeding-disease-bar" style={{width: `${bar}%`}}/>
            </div>
            <div className="breeding-disease-footer">
                <span className="breeding-disease-risk">{riskPct(data.risk)}</span>
                <span className="breeding-disease-level">
                    {data.level === "low" ? "Низкий" : data.level === "medium" ? "Средний" : "Высокий"}
                </span>
            </div>
        </div>
    );
}

export default function BreedingPage() {
    const [sire, setSire] = useState<DogListItem | null>(null);
    const [dam, setDam] = useState<DogListItem | null>(null);
    const [result, setResult] = useState<BreedingResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const canAnalyse = sire !== null && dam !== null;

    const handleAnalyse = async () => {
        if (!sire || !dam) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const resp = await fetch(`/api/dogs/breeding/predict/?sire_id=${sire.id}&dam_id=${dam.id}`);
            if (!resp.ok) throw new Error(`Ошибка ${resp.status}`);
            setResult(await resp.json());
        } catch (e) {
            setError(e instanceof Error ? e.message : "Неизвестная ошибка");
        } finally {
            setLoading(false);
        }
    };

    const verdict = result ? VERDICT[result.recommendation] : null;

    return (
        <main className="breeding-page">
            <div className="breeding-container">

                {/* Hero */}
                <div className="breeding-hero">
                    <div className="breeding-hero-content">
                        <div className="breeding-hero-icon">🧬</div>
                        <div>
                            <h1>Прогноз вязки</h1>
                            <p>
                                Анализирует родословную и результаты здоровья родителей.
                                Прогнозирует вероятность наследственных заболеваний у потомства
                                на основе генетических данных породы.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Selectors */}
                <div className="breeding-selector-grid">
                    <DogSelector sex={1} selected={sire} onSelect={setSire} onClear={() => {
                        setSire(null);
                        setResult(null);
                    }}/>
                    <DogSelector sex={2} selected={dam} onSelect={setDam} onClear={() => {
                        setDam(null);
                        setResult(null);
                    }}/>
                </div>

                {/* Button */}
                <div className="breeding-analyse-wrap">
                    <button className="breeding-analyse-btn" disabled={!canAnalyse || loading} onClick={handleAnalyse}>
                        {loading
                            ? <><span className="btn-spinner"/> Анализируем…</>
                            : <><span>🔬</span> Рассчитать прогноз</>}
                    </button>
                </div>

                {error && <div className="breeding-error"><span>⚠️</span> {error}</div>}

                {result && verdict && (
                    <div className="breeding-results">

                        <div className={`breeding-verdict breeding-verdict--${result.recommendation}`}>
                            <div className="breeding-verdict-emoji">{verdict.emoji}</div>
                            <div className="breeding-verdict-body">
                                <div className="breeding-verdict-title">{verdict.title}</div>
                                <div className="breeding-verdict-sub">{verdict.sub}</div>
                            </div>
                            <div className="breeding-verdict-meta">
                                {result.offspring_coi != null && (
                                    <div className="breeding-verdict-badge">
                                        <div className="breeding-verdict-badge-label">COI потомства</div>
                                        <div
                                            className="breeding-verdict-badge-value">{result.offspring_coi.toFixed(2)}%
                                        </div>
                                    </div>
                                )}
                                <div className="breeding-verdict-badge">
                                    <div className="breeding-verdict-badge-label">Уверенность</div>
                                    <div
                                        className="breeding-verdict-badge-value">{CONFIDENCE_LABELS[result.confidence]}</div>
                                </div>
                            </div>
                        </div>

                        {result.coi_info && (
                            <div className="breeding-coi-card" style={{borderColor: COI_COLORS[result.coi_info.level]}}>
                                <div className="breeding-coi-header">
                                    <span className="breeding-coi-icon">🧬</span>
                                    <span className="breeding-coi-title"
                                          style={{color: COI_COLORS[result.coi_info.level]}}>
                                        {result.coi_info.title}
                                    </span>
                                </div>
                                <p className="breeding-coi-text">{result.coi_info.text}</p>
                            </div>
                        )}

                        <div className="breeding-section-title">
                            ML прогноз
                        </div>
                        <div className="breeding-ml-grid">
                            {(Object.entries(ML_DISEASES) as [keyof BreedingResult, string][]).map(([key, label]) => (
                                <DiseaseCard key={key} name={label} data={result[key] as DiseaseRisk}/>
                            ))}
                        </div>

                    </div>
                )}

                <p className="breeding-disclaimer">
                    Прогноз носит информационный характер и не является ветеринарным заключением.
                    Сайт не несёт ответственности за результаты вязки.
                    Перед принятием решения рекомендуется консультация с ветеринарным специалистом.
                </p>

            </div>
        </main>
    );
}


