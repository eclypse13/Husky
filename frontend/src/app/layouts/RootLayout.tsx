import { Outlet } from "react-router-dom";
import Header from "@/components/Header";

export default function RootLayout() {
    return (
        <>
            <Header />
            <main className="pt-20">
                <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8">
                    <Outlet />
                </div>
            </main>
        </>
    );
}
