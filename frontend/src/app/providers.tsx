import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import type { PropsWithChildren } from "react";

export function AppProviders({ children }: PropsWithChildren) {
    const [qc] = useState(() => new QueryClient());
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}