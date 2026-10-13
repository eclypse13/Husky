import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { fetchPuppy, savePuppy } from "@/api/puppies";
import { apiFetch, useAuth } from "@/lib/auth";
import { DEFAULT_DOG_IMG } from "@/utils/dogPhoto";
import { compressImages } from "@/utils/imageCompress";
import type { DogListItem } from "@/types/dog";
import type { PuppyPhoto } from "@/types/puppy";
import "./Puppies.css";

/** Автокомплит родителя по архиву с возможностью ручного ввода. */
function ParentPicker({
    sex,
    label,
    value,
    onChange,
}: {
    sex: 1 | 2;
    label: string;
    value: { id: number | null; name: string };
    onChange: (v: { id: number | null; name: string }) => void;
}) {
    const [query, setQuery] = useState(value.name);
    const [open, setOpen] = useState(false);
    const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
    const [dQuery, setDQuery] = useState("");

    // Данные анкеты приходят асинхронно уже после монтирования — подтягиваем
    // имя родителя в поле, когда оно приходит/меняется извне (режим редактирования).
    useEffect(() => {
        setQuery(value.name);
    }, [value.name]);

    const { data, isFetching } = useQuery<{ results: DogListItem[] }>({
        queryKey: ["parent-search", sex, dQuery],
        queryFn: () => apiFetch(`/api/dogs/?sex=${sex}&q=${encodeURIComponent(dQuery)}&per_page=8`).then((r) => r.json()),
        enabled: dQuery.length >= 2,
        staleTime: 10_000,
    });

    return (
        <div className="puppy-parent-picker">
            <label className="puppy-field__label">{label}</label>
            <div className="puppy-parent-input">
                <input
                    value={query}
                    placeholder="Введите имя (можно из архива)…"
                    onChange={(e) => {
                        const v = e.target.value;
                        setQuery(v);
                        // ручной ввод сбрасывает привязку к архиву
                        onChange({ id: null, name: v });
                        clearTimeout(timer.current);
                        timer.current = setTimeout(() => {
                            setDQuery(v);
                            setOpen(v.length >= 2);
                        }, 250);
                    }}
                    onFocus={() => query.length >= 2 && setOpen(true)}
                    onBlur={() => setTimeout(() => setOpen(false), 150)}
                    autoComplete="off"
                />
                {value.id && <span className="puppy-parent-linked" title="Связано с архивом">🔗 архив</span>}
                {open && (
                    <div className="puppy-parent-dropdown">
                        {isFetching && <div className="puppy-parent-empty">Поиск…</div>}
                        {!isFetching && !data?.results?.length && (
                            <div className="puppy-parent-empty">Ничего не найдено — оставим как текст</div>
                        )}
                        {!isFetching &&
                            data?.results?.map((dog) => (
                                <button
                                    type="button"
                                    key={dog.id}
                                    className="puppy-parent-option"
                                    onMouseDown={() => {
                                        onChange({ id: dog.id, name: dog.registered_name });
                                        setQuery(dog.registered_name);
                                        setOpen(false);
                                    }}
                                >
                                    <span>{dog.registered_name}</span>
                                    {dog.year_of_birth && <small>{dog.year_of_birth}</small>}
                                </button>
                            ))}
                    </div>
                )}
            </div>
        </div>
    );
}

interface NewPhoto {
    file: File;
    url: string;
}

export default function PuppyForm() {
    const { id } = useParams<{ id: string }>();
    const isEdit = Boolean(id);
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { isAuthenticated, user } = useAuth();

    const [name, setName] = useState("");
    const [sex, setSex] = useState("");
    const [description, setDescription] = useState("");
    const [dateOfBirth, setDateOfBirth] = useState("");
    const [color, setColor] = useState("");
    const [city, setCity] = useState("");
    const [price, setPrice] = useState("");
    const [kennelName, setKennelName] = useState("");
    const [kennelUrl, setKennelUrl] = useState("");
    const [breederContact, setBreederContact] = useState("");
    const [status, setStatus] = useState("available");
    const [isPublished, setIsPublished] = useState(true);
    const [sire, setSire] = useState<{ id: number | null; name: string }>({ id: null, name: "" });
    const [dam, setDam] = useState<{ id: number | null; name: string }>({ id: null, name: "" });

    const [existingPhotos, setExistingPhotos] = useState<PuppyPhoto[]>([]);
    const [removeIds, setRemoveIds] = useState<number[]>([]);
    const [newPhotos, setNewPhotos] = useState<NewPhoto[]>([]);

    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [processing, setProcessing] = useState(false);

    const { data: loaded } = useQuery({
        queryKey: ["puppy", id],
        queryFn: () => fetchPuppy(id!),
        enabled: isEdit,
    });

    useEffect(() => {
        if (!loaded) return;
        setName(loaded.name);
        setSex(loaded.sex || "");
        setDescription(loaded.description || "");
        setDateOfBirth(loaded.date_of_birth ? loaded.date_of_birth.slice(0, 10) : "");
        setColor(loaded.color || "");
        setCity(loaded.city || "");
        setPrice(loaded.price ? String(Number(loaded.price)) : "");
        setKennelName(loaded.kennel_name || "");
        setKennelUrl(loaded.kennel_url || "");
        setBreederContact(loaded.breeder_contact || "");
        setStatus(loaded.status || "available");
        setIsPublished(loaded.is_published);
        setSire({ id: loaded.sire_archive_id, name: loaded.sire_name || "" });
        setDam({ id: loaded.dam_archive_id, name: loaded.dam_name || "" });
        setExistingPhotos(loaded.photos || []);
    }, [loaded]);

    // очистка object URL
    useEffect(() => {
        return () => newPhotos.forEach((p) => URL.revokeObjectURL(p.url));
    }, [newPhotos]);

    if (!isAuthenticated) {
        return (
            <div className="puppies-state">
                Чтобы разместить объявление, нужно{" "}
                <Link to={`/login?redirect=${encodeURIComponent(isEdit ? `/puppies/${id}/edit` : "/puppies/new")}`}>
                    войти
                </Link>
                .
            </div>
        );
    }

    const addFiles = async (files: FileList | null) => {
        if (!files) return;
        const images = Array.from(files).filter((f) => f.type.startsWith("image/"));
        if (!images.length) return;
        // Сжимаем в браузере, чтобы не отправлять на сервер тяжёлые оригиналы
        // (иначе крупные фото обрывают запрос — "Failed to fetch").
        setProcessing(true);
        try {
            const compressed = await compressImages(images);
            const arr = compressed.map((file) => ({ file, url: URL.createObjectURL(file) }));
            setNewPhotos((prev) => [...prev, ...arr]);
        } finally {
            setProcessing(false);
        }
    };

    const removeExisting = (photoId: number) => {
        setRemoveIds((prev) => [...prev, photoId]);
        setExistingPhotos((prev) => prev.filter((p) => p.id !== photoId));
    };

    const removeNew = (idx: number) => {
        setNewPhotos((prev) => {
            const copy = [...prev];
            URL.revokeObjectURL(copy[idx].url);
            copy.splice(idx, 1);
            return copy;
        });
    };

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!name.trim()) return setError("Укажите кличку щенка");
        if (!breederContact.trim()) return setError("Укажите контакт заводчика");

        const fd = new FormData();
        fd.set("name", name.trim());
        fd.set("sex", sex);
        fd.set("description", description);
        if (dateOfBirth) fd.set("date_of_birth", dateOfBirth);
        fd.set("color", color);
        fd.set("city", city);
        if (price) fd.set("price", price);
        fd.set("kennel_name", kennelName);
        if (kennelUrl) fd.set("kennel_url", kennelUrl);
        fd.set("breeder_contact", breederContact.trim());
        fd.set("status", status);
        fd.set("is_published", isPublished ? "true" : "false");
        fd.set("sire_name", sire.name);
        if (sire.id) fd.set("sire_archive_id", String(sire.id));
        fd.set("dam_name", dam.name);
        if (dam.id) fd.set("dam_archive_id", String(dam.id));

        newPhotos.forEach((p) => fd.append("photos", p.file));
        if (removeIds.length) fd.set("remove_photo_ids", removeIds.join(","));

        setSaving(true);
        try {
            const saved = await savePuppy(fd, isEdit ? id : undefined);
            queryClient.invalidateQueries({ queryKey: ["puppies"] });
            queryClient.invalidateQueries({ queryKey: ["puppy", String(saved.id)] });
            navigate(`/puppies/${saved.id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось сохранить");
            setSaving(false);
        }
    };

    return (
        <div className="puppies-page">
            <Breadcrumb
                title={isEdit ? "Редактирование" : "Новое объявление"}
                items={[
                    { label: "Главная", to: "/" },
                    { label: "Щенки", to: "/puppies" },
                    { label: isEdit ? "Редактирование" : "Новое объявление" },
                ]}
            />

            <main className="puppies-main">
                <div className="content-container puppy-form-wrap">
                    <form className="puppy-form" onSubmit={submit}>
                        {/* Фото */}
                        <section className="puppy-form__block">
                            <h3 className="puppy-form__legend">Фотографии</h3>
                            <p className="puppy-form__hint">
                                Можно выбрать несколько фото сразу. Все фото автоматически приводятся к единому размеру.
                            </p>
                            <div className="puppy-uploader">
                                {existingPhotos.map((ph) => (
                                    <div className="puppy-thumb" key={`e-${ph.id}`}>
                                        <img src={ph.image || DEFAULT_DOG_IMG} alt="" />
                                        <button type="button" onClick={() => removeExisting(ph.id)} aria-label="Удалить">✕</button>
                                    </div>
                                ))}
                                {newPhotos.map((p, i) => (
                                    <div className="puppy-thumb" key={`n-${i}`}>
                                        <img src={p.url} alt="" />
                                        <button type="button" onClick={() => removeNew(i)} aria-label="Удалить">✕</button>
                                    </div>
                                ))}
                                <label className="puppy-upload-tile">
                                    <input
                                        type="file"
                                        accept="image/*"
                                        multiple
                                        onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
                                        hidden
                                    />
                                    <span>＋</span>
                                    <small>Добавить</small>
                                </label>
                            </div>
                            {processing && <p className="puppy-form__hint">Обработка фотографий…</p>}
                        </section>

                        {/* Основное */}
                        <section className="puppy-form__block">
                            <h3 className="puppy-form__legend">О щенке</h3>
                            <div className="puppy-form__grid">
                                <label className="puppy-field puppy-field--full">
                                    <span className="puppy-field__label">Кличка *</span>
                                    <input value={name} onChange={(e) => setName(e.target.value)} required />
                                </label>

                                <label className="puppy-field">
                                    <span className="puppy-field__label">Пол</span>
                                    <select value={sex} onChange={(e) => setSex(e.target.value)}>
                                        <option value="">—</option>
                                        <option value="male">Кобель</option>
                                        <option value="female">Сука</option>
                                    </select>
                                </label>

                                <label className="puppy-field">
                                    <span className="puppy-field__label">Дата рождения</span>
                                    <input type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)} />
                                </label>

                                <label className="puppy-field">
                                    <span className="puppy-field__label">Окрас</span>
                                    <input value={color} onChange={(e) => setColor(e.target.value)} />
                                </label>

                                <label className="puppy-field">
                                    <span className="puppy-field__label">Статус</span>
                                    <select value={status} onChange={(e) => setStatus(e.target.value)}>
                                        <option value="available">Доступен</option>
                                        <option value="reserved">Забронирован</option>
                                        <option value="sold">Продан</option>
                                    </select>
                                </label>

                                <label className="puppy-field puppy-field--full">
                                    <span className="puppy-field__label">Описание</span>
                                    <textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />
                                </label>
                            </div>
                        </section>

                        {/* Родители */}
                        <section className="puppy-form__block">
                            <h3 className="puppy-form__legend">Родители</h3>
                            <p className="puppy-form__hint">
                                Начните вводить имя — если родитель есть в архиве, выберите его для ссылки на страницу.
                            </p>
                            <div className="puppy-form__grid">
                                <ParentPicker sex={1} label="Отец" value={sire} onChange={setSire} />
                                <ParentPicker sex={2} label="Мать" value={dam} onChange={setDam} />
                            </div>
                        </section>

                        {/* Питомник и контакты */}
                        <section className="puppy-form__block">
                            <h3 className="puppy-form__legend">Питомник и контакты</h3>
                            <div className="puppy-form__grid">
                                <label className="puppy-field">
                                    <span className="puppy-field__label">Питомник</span>
                                    <input value={kennelName} onChange={(e) => setKennelName(e.target.value)} />
                                </label>
                                <label className="puppy-field">
                                    <span className="puppy-field__label">Ссылка на питомник</span>
                                    <input type="url" placeholder="https://…" value={kennelUrl} onChange={(e) => setKennelUrl(e.target.value)} />
                                </label>
                                <label className="puppy-field">
                                    <span className="puppy-field__label">Город</span>
                                    <input value={city} onChange={(e) => setCity(e.target.value)} />
                                </label>
                                <label className="puppy-field">
                                    <span className="puppy-field__label">Цена, ₽</span>
                                    <input type="number" min="0" step="1" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Пусто = договорная" />
                                </label>
                                <label className="puppy-field puppy-field--full">
                                    <span className="puppy-field__label">Контакт заводчика *</span>
                                    <input value={breederContact} onChange={(e) => setBreederContact(e.target.value)} placeholder="Телефон, Telegram, email…" required />
                                </label>
                            </div>

                            <div className="puppy-nkp-note">
                                {user?.is_nkp_member ? (
                                    <>🌟 Отметка «питомник — член НКП» будет добавлена автоматически.</>
                                ) : (
                                    <>Отметка НКП присваивается членам клуба автоматически по профилю.</>
                                )}
                            </div>

                            <label className="puppy-visibility">
                                <input
                                    type="checkbox"
                                    checked={isPublished}
                                    onChange={(e) => setIsPublished(e.target.checked)}
                                />
                                <span>
                                    <strong>Опубликовать объявление</strong>
                                    <small>
                                        Снимите галочку, чтобы скрыть анкету — её увидите только вы.
                                        Публикацию можно вернуть в любой момент.
                                    </small>
                                </span>
                            </label>
                        </section>

                        {error && <div className="auth-error">⚠️ {error}</div>}

                        <div className="puppy-form__actions">
                            <button type="submit" className="puppy-btn puppy-btn--primary" disabled={saving || processing}>
                                {saving ? "Сохранение…" : processing ? "Обработка фото…" : isEdit ? "Сохранить изменения" : "Опубликовать"}
                            </button>
                            <Link to={isEdit ? `/puppies/${id}` : "/puppies"} className="puppy-btn puppy-btn--soft">
                                Отмена
                            </Link>
                        </div>
                    </form>
                </div>
            </main>
        </div>
    );
}
