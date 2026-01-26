"use client";

import React, { useEffect, useRef, useState } from "react";

export interface InteractiveGridBackgroundProps
    extends React.HTMLProps<HTMLDivElement> {
    gridSize?: number;
    gridColor?: string;
    darkGridColor?: string;
    effectColor?: string;
    darkEffectColor?: string;
    trailLength?: number;
    width?: number;
    height?: number;
    idleSpeed?: number;
    glow?: boolean;
    glowRadius?: number;
    children?: React.ReactNode;
    showFade?: boolean;
    fadeIntensity?: number;
    idleRandomCount?: number; // ✅ how many random cells move during idle
}

const InteractiveGridBackground: React.FC<InteractiveGridBackgroundProps> = ({
    gridSize = 50,
    gridColor = "#e5e7eb",
    darkGridColor = "#27272a",
    effectColor = "rgba(0, 0, 0, 0.5)",
    darkEffectColor = "rgba(255, 255, 255, 0.5)",
    trailLength = 1,
    width,
    height,
    idleSpeed = 0.2,
    glow = true,
    glowRadius = 20,
    children,
    showFade = true,
    fadeIntensity = 20,
    idleRandomCount = 5,
    className,
    ...props
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [isDarkMode, setIsDarkMode] = useState(false);

    const trailRef = useRef<{ x: number; y: number }[]>([]);
    const idleTargetsRef = useRef<{ x: number; y: number }[]>([]);
    const idlePositionsRef = useRef<{ x: number; y: number }[]>([]);
    const mouseActiveRef = useRef(false);
    const lastMouseTimeRef = useRef(0);

    // Detect dark mode
    useEffect(() => {
        const updateDarkMode = () => {
            const prefersDark =
                window.matchMedia &&
                window.matchMedia("(prefers-color-scheme: dark)").matches;
            setIsDarkMode(
                document.documentElement.classList.contains("dark") || prefersDark
            );
        };
        updateDarkMode();
        const observer = new MutationObserver(() => updateDarkMode());
        observer.observe(document.documentElement, { attributes: true });
        return () => observer.disconnect();
    }, []);

    // Mouse tracking
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            const container = containerRef.current;
            if (!container) return;
            const rect = container.getBoundingClientRect();
            const rawX = e.clientX - rect.left;
            const rawY = e.clientY - rect.top;

            if (rawX < 0 || rawY < 0 || rawX > rect.width || rawY > rect.height)
                return;

            mouseActiveRef.current = true;
            lastMouseTimeRef.current = Date.now();

            const snappedX = Math.floor(rawX / gridSize);
            const snappedY = Math.floor(rawY / gridSize);

            const last = trailRef.current[0];
            if (!last || last.x !== snappedX || last.y !== snappedY) {
                trailRef.current.unshift({ x: snappedX, y: snappedY });
                if (trailRef.current.length > trailLength) trailRef.current.pop();
            }
        };

        window.addEventListener("mousemove", handleMouseMove);
        return () => window.removeEventListener("mousemove", handleMouseMove);
    }, [gridSize, trailLength]);

    // Drawing logic
    useEffect(() => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        if (!canvas || !container) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Use container dimensions if specific width/height not provided
        const updateDimensions = () => {
            const newWidth = width || container.clientWidth;
            const newHeight = height || container.clientHeight;

            if (canvas.width !== newWidth || canvas.height !== newHeight) {
                canvas.width = newWidth;
                canvas.height = newHeight;
                return true;
            }
            return false;
        };

        // Initial sizing
        updateDimensions();

        const canvasWidth = canvas.width;
        const canvasHeight = canvas.height;

        const cols = Math.floor(canvasWidth / gridSize);
        const rows = Math.floor(canvasHeight / gridSize);

        const lineColor = isDarkMode ? darkGridColor : gridColor;
        const glowColor = isDarkMode ? darkEffectColor : effectColor;

        // Initialize idle positions
        if (idleTargetsRef.current.length === 0) {
            idleTargetsRef.current = Array.from({ length: idleRandomCount }, () => ({
                x: Math.floor(Math.random() * cols),
                y: Math.floor(Math.random() * rows),
            }));
            idlePositionsRef.current = idleTargetsRef.current.map((p) => ({ ...p }));
        }

        let animationFrameId: number;

        const draw = () => {
            // Check if dimensions changed (handle resize)
            const currentWidth = width || container.clientWidth;
            const currentHeight = height || container.clientHeight;

            if (canvas.width !== currentWidth || canvas.height !== currentHeight) {
                canvas.width = currentWidth;
                canvas.height = currentHeight;
            }

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw grid lines
            ctx.strokeStyle = lineColor;
            ctx.lineWidth = 1;
            for (let x = 0; x <= canvas.width; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            }
            for (let y = 0; y <= canvas.height; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }

            // Idle animation logic
            const idleThreshold = 2000;
            if (Date.now() - lastMouseTimeRef.current > idleThreshold) {
                mouseActiveRef.current = false;

                idlePositionsRef.current.forEach((pos, i) => {
                    const target = idleTargetsRef.current[i];
                    const dx = target.x - pos.x;
                    const dy = target.y - pos.y;

                    if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01) {
                        // new random target when reached
                        const currentCols = Math.floor(canvas.width / gridSize);
                        const currentRows = Math.floor(canvas.height / gridSize);
                        idleTargetsRef.current[i] = {
                            x: Math.floor(Math.random() * currentCols),
                            y: Math.floor(Math.random() * currentRows),
                        };
                    } else {
                        pos.x += dx * idleSpeed;
                        pos.y += dy * idleSpeed;
                    }

                    const roundedX = Math.round(pos.x);
                    const roundedY = Math.round(pos.y);
                    const last = trailRef.current[0];
                    if (!last || last.x !== roundedX || last.y !== roundedY) {
                        trailRef.current.unshift({ x: roundedX, y: roundedY });
                        if (trailRef.current.length > trailLength * idleRandomCount)
                            trailRef.current.pop();
                    }
                });
            }

            // Draw trail glow
            trailRef.current.forEach((cell, idx) => {
                const alpha = 1 - idx * (1 / (trailLength + 1));
                const rgbaColor = glowColor.replace(/[\d.]+\)$/g, `${alpha})`);

                ctx.fillStyle = rgbaColor;
                if (glow) {
                    ctx.shadowColor = rgbaColor;
                    ctx.shadowBlur = glowRadius;
                } else {
                    ctx.shadowBlur = 0;
                }

                ctx.fillRect(cell.x * gridSize, cell.y * gridSize, gridSize, gridSize);
            });

            animationFrameId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            if (animationFrameId) cancelAnimationFrame(animationFrameId);
        };
    }, [
        gridSize,
        width, // trigger re-init if explicit dims change
        height,
        gridColor,
        darkGridColor,
        effectColor,
        darkEffectColor,
        isDarkMode,
        trailLength,
        idleSpeed,
        glow,
        glowRadius,
        idleRandomCount,
    ]);

    return (
        <div
            ref={containerRef}
            className={`relative ${className}`}
            style={{ width: width || "100%", height: height || "100%" }}
            {...props}
        >
            <canvas
                ref={canvasRef}
                className="absolute top-0 left-0 z-0 pointer-events-none"
            />

            {showFade && (
                <div
                    className="pointer-events-none absolute inset-0 bg-white dark:bg-black"
                    style={{
                        maskImage: `radial-gradient(ellipse at center, transparent ${fadeIntensity}%, black)`,
                        WebkitMaskImage: `radial-gradient(ellipse at center, transparent ${fadeIntensity}%, black)`,
                    }}
                />
            )}
            <div className="relative z-0 w-full h-full">{children}</div>
        </div>
    );
};

export default InteractiveGridBackground;
