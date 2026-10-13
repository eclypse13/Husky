import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import type { PropsWithChildren } from "react";
import { AuthProvider } from "@/lib/auth";

export function AppProviders({ children }: PropsWithChildren) {
    const [qc] = useState(() => new QueryClient());
    return (
        <QueryClientProvider client={qc}>
            <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
    );
}
