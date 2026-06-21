import {useEffect} from "react";
import {useQuery} from "@tanstack/react-query";
import "./HealthModal.css";

interface MedicalRecord {
    id?: number;
    ofa_number: string | null;
    registry: string;
    group: string | null;
    conclusion: string | null;
    score: number | null;
    test_date: string | null;
    report_date: string | null;
    age_in_months: number | null;
}

interface ApiResponse {
    dog_id?: number;
    records?: MedicalRecord[];
}

interface Props {
    dogId: number;
    dogName?: string;
    onClose: () => void;
}


function formatDate(raw: string | null): string | null {
    if (!raw) return null;
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit", year: "numeric"});
}

export default function HealthModal({dogId, dogName: _dogName, onClose}: Props) {
    const {data, isLoading, error} = useQuery<ApiResponse>({
        queryKey: ["dog-health", dogId],
        queryFn: async () => {
            const resp = await fetch(`/api/dogs/health/records/?dog_id=${dogId}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return resp.json();
        },
        staleTime: 60_000,
    });

    // Поддержка обоих форматов ответа: {results: [...]} или просто [...]
    const records: MedicalRecord[] = Array.isArray(data)
        ? data
        : (data?.records ?? []);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose();
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [onClose]);

    useEffect(() => {
        document.body.style.overflow = "hidden";
        return () => {
            document.body.style.overflow = "";
        };
    }, []);

    return (
        <div className="hm-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
            <div className="hm-inner">
                <div className="hm-head">
                    <h3 className="hm-title">Медицинские тесты</h3>
                    <button className="hm-close" onClick={onClose}>✕</button>
                </div>

                {isLoading && (
                    <div className="hm-empty">Загрузка…</div>
                )}

                {!isLoading && error && (
                    <div className="hm-empty">
                        <span>⚠️</span>
                        <p>Ошибка загрузки</p>
                    </div>
                )}

                {!isLoading && !error && records.length === 0 && (
                    <div className="hm-empty">
                        <span>📋</span>
                        <p>Информация отсутствует</p>
                    </div>
                )}

                {!isLoading && !error && records.length > 0 && (
                    <div className="hm-table-wrap">
                        <table className="hm-table">
                            <thead>
                            <tr>
                                <th>Registry</th>
                                <th>Result</th>
                                <th>Test Date</th>
                                <th>OFA #</th>
                            </tr>
                            </thead>
                            <tbody>
                            {records.map((r, i) => (
                                <tr key={r.id ?? r.ofa_number ?? i}>
                                    <td>{r.registry}</td>
                                    <td style={{fontWeight: 600}}>
                                        {r.conclusion || "—"}
                                    </td>
                                    <td className="hm-muted">{formatDate(r.test_date ?? r.report_date) || "—"}</td>
                                    <td className="hm-muted">{r.ofa_number || "—"}</td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
