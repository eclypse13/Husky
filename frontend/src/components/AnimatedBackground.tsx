import { useEffect, useRef } from "react";
import "./AnimatedBackground.css";

export default function AnimatedBackground() {
    const shapesRef = useRef<Array<HTMLDivElement | null>>([]);

    const setShapeRef =
        (i: number) =>
            (el: HTMLDivElement | null): void => {
                shapesRef.current[i] = el;
            };

    useEffect(() => {
        const onScroll = () => {
            const y = window.scrollY;
            shapesRef.current.forEach((el, i) => {
                if (!el) return;
                const speed = 0.35 + i * 0.1;
                el.style.transform = `translateY(${y * speed}px)`;
            });
        };
        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);

    return (
        <div className="animated-bg" aria-hidden>
            <div className="floating-shapes">
                <div className="shape shape-1" ref={setShapeRef(0)} />
                <div className="shape shape-2" ref={setShapeRef(1)} />
                <div className="shape shape-3" ref={setShapeRef(2)} />
            </div>
        </div>
    );
}
