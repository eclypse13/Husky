import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type PropsWithChildren,
} from "react";

export interface AuthUser {
    email: string;
    name: string;
    first_name: string;
    last_name: string;
    is_nkp_member: boolean;
    is_staff: boolean;
}

interface AuthState {
    token: string | null;
    user: AuthUser | null;
}

interface AuthContextValue extends AuthState {
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (payload: RegisterPayload) => Promise<void>;
    logout: () => void;
}

export interface RegisterPayload {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    phone?: string;
    city?: string;
}

const TOKEN_KEY = "nkp_auth_token";
const USER_KEY = "nkp_auth_user";

const AuthContext = createContext<AuthContextValue | null>(null);

function readStored(): AuthState {
    try {
        const token = localStorage.getItem(TOKEN_KEY);
        const rawUser = localStorage.getItem(USER_KEY);
        return {
            token: token || null,
            user: rawUser ? (JSON.parse(rawUser) as AuthUser) : null,
        };
    } catch {
        return { token: null, user: null };
    }
}

/**
 * Обёртка над fetch, добавляющая токен авторизации.
 * Ходим строго по токену (credentials: "omit"), чтобы не смешивать
 * с session-аутентификацией и не упираться в CSRF.
 */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
    let token: string | null = null;
    try {
        token = localStorage.getItem(TOKEN_KEY);
    } catch {
        token = null;
    }

    const headers = new Headers(init.headers || {});
    if (token) headers.set("Authorization", `Token ${token}`);

    return fetch(input, {
        ...init,
        headers,
        credentials: "omit",
    });
}

function persist(state: AuthState) {
    try {
        if (state.token) localStorage.setItem(TOKEN_KEY, state.token);
        else localStorage.removeItem(TOKEN_KEY);
        if (state.user) localStorage.setItem(USER_KEY, JSON.stringify(state.user));
        else localStorage.removeItem(USER_KEY);
    } catch {
        /* ignore storage errors */
    }
}

export function AuthProvider({ children }: PropsWithChildren) {
    const [state, setState] = useState<AuthState>(() => readStored());

    useEffect(() => {
        persist(state);
    }, [state]);

    const applyAuth = useCallback((data: { token: string; user: AuthUser }) => {
        setState({ token: data.token, user: data.user });
    }, []);

    const login = useCallback(
        async (email: string, password: string) => {
            const res = await fetch("/api/auth/login/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "omit",
                body: JSON.stringify({ email, password }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.error || "Не удалось войти");
            applyAuth(data);
        },
        [applyAuth]
    );

    const register = useCallback(
        async (payload: RegisterPayload) => {
            const res = await fetch("/api/auth/register/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "omit",
                body: JSON.stringify(payload),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                const msg =
                    data.error ||
                    (typeof data === "object" ? Object.values(data).flat().join(" ") : "") ||
                    "Не удалось зарегистрироваться";
                throw new Error(msg);
            }
            applyAuth(data);
        },
        [applyAuth]
    );

    const logout = useCallback(() => {
        // best-effort серверный logout (не критичен при токене)
        apiFetch("/api/auth/logout/", { method: "POST" }).catch(() => {});
        setState({ token: null, user: null });
    }, []);

    const value = useMemo<AuthContextValue>(
        () => ({
            ...state,
            isAuthenticated: Boolean(state.token),
            login,
            register,
            logout,
        }),
        [state, login, register, logout]
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
    return ctx;
}
