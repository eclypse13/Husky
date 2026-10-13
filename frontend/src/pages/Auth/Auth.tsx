import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Breadcrumb from "@/components/Breadcrumb/Breadcrumb";
import { useAuth } from "@/lib/auth";
import "./Auth.css";

type Mode = "login" | "register";

export default function Auth() {
    const { login, register } = useAuth();
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const redirect = params.get("redirect") || "/puppies";

    const [mode, setMode] = useState<Mode>("login");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [phone, setPhone] = useState("");
    const [city, setCity] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);
        try {
            if (mode === "login") {
                await login(email, password);
            } else {
                await register({
                    email,
                    password,
                    first_name: firstName,
                    last_name: lastName,
                    phone,
                    city,
                });
            }
            navigate(redirect);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Ошибка");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <Breadcrumb
                title={mode === "login" ? "Вход" : "Регистрация"}
                items={[{ label: "Главная", to: "/" }, { label: mode === "login" ? "Вход" : "Регистрация" }]}
            />

            <main className="auth-main">
                <div className="auth-card">
                    <div className="auth-tabs">
                        <button
                            type="button"
                            className={`auth-tab ${mode === "login" ? "is-active" : ""}`}
                            onClick={() => { setMode("login"); setError(null); }}
                        >
                            Вход
                        </button>
                        <button
                            type="button"
                            className={`auth-tab ${mode === "register" ? "is-active" : ""}`}
                            onClick={() => { setMode("register"); setError(null); }}
                        >
                            Регистрация
                        </button>
                    </div>

                    <form className="auth-form" onSubmit={submit}>
                        <label className="auth-field">
                            <span>Email</span>
                            <input
                                type="email"
                                autoComplete="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@example.com"
                            />
                        </label>

                        <label className="auth-field">
                            <span>Пароль</span>
                            <input
                                type="password"
                                autoComplete={mode === "login" ? "current-password" : "new-password"}
                                required
                                minLength={6}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Минимум 6 символов"
                            />
                        </label>

                        {mode === "register" && (
                            <>
                                <div className="auth-row">
                                    <label className="auth-field">
                                        <span>Имя</span>
                                        <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                                    </label>
                                    <label className="auth-field">
                                        <span>Фамилия</span>
                                        <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
                                    </label>
                                </div>
                                <div className="auth-row">
                                    <label className="auth-field">
                                        <span>Телефон</span>
                                        <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+7…" />
                                    </label>
                                    <label className="auth-field">
                                        <span>Город</span>
                                        <input value={city} onChange={(e) => setCity(e.target.value)} />
                                    </label>
                                </div>
                            </>
                        )}

                        {error && <div className="auth-error">⚠️ {error}</div>}

                        <button type="submit" className="auth-submit" disabled={loading}>
                            {loading ? "Подождите…" : mode === "login" ? "Войти" : "Создать аккаунт"}
                        </button>
                    </form>

                    <p className="auth-switch">
                        {mode === "login" ? (
                            <>Нет аккаунта?{" "}
                                <button type="button" className="auth-link" onClick={() => setMode("register")}>
                                    Зарегистрироваться
                                </button>
                            </>
                        ) : (
                            <>Уже есть аккаунт?{" "}
                                <button type="button" className="auth-link" onClick={() => setMode("login")}>
                                    Войти
                                </button>
                            </>
                        )}
                    </p>
                    <p className="auth-back">
                        <Link to="/puppies">← К объявлениям</Link>
                    </p>
                </div>
            </main>
        </div>
    );
}
