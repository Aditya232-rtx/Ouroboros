"use client";

import Header from "../components/Header";
import TabNavigation from "../components/TabNavigation";
import InteractiveGridBackground from "../components/InteractiveGridBackground";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 relative">
            <div className="fixed inset-0 z-0 opacity-20 pointer-events-none">
                <InteractiveGridBackground
                    className="h-full w-full"
                    gridColor="#94a3b8"
                    darkGridColor="#1e293b"
                />
            </div>

            <div className="relative z-10 flex flex-col min-h-screen">
                <Header />
                <TabNavigation />
                <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto w-full">
                    {children}
                </main>
            </div>
        </div>
    );
}
