import { Outlet } from "react-router-dom";
import AnimatedBackground from "@/components/AnimatedBackground";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ScrollToTop from "@/components/ScrollToTop";
import SiteBanner from "@/components/SiteBanner";
import { useEffect } from "react";

export default function RootLayout() {
    useEffect(() => {
        const setOffset = () => {
            const headerEl = document.querySelector<HTMLElement>("header.header");
            const h = headerEl?.offsetHeight ?? 96;
            document.documentElement.style.setProperty("--header-height", `${h}px`);
        };
        setOffset();
        window.addEventListener("resize", setOffset);
        return () => window.removeEventListener("resize", setOffset);
    }, []);

    return (
        <>
            <ScrollToTop />
            <AnimatedBackground />
            <Header />
            <main id="page-content">
                <Outlet />
            </main>
            <Footer />
            <SiteBanner />
        </>
    );
}
