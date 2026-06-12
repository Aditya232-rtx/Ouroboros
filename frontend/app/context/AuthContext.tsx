"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

interface User {
    id: number;
    user_id: string;
    email: string;
    full_name?: string;
    is_active: boolean;
    created_at: string;
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (token: string) => void;
    logout: () => void;
    isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    login: () => { },
    logout: () => { },
    isAuthenticated: false,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    // Fetch current user on mount
    useEffect(() => {
        async function loadUser() {
            try {
                const response = await fetch("/api/proxy/auth/me", {
                    headers: {
                        "Content-Type": "application/json",
                    },
                    credentials: "include",
                });

                if (response.ok) {
                    const userData = await response.json();
                    setUser(userData);
                } else {
                    setUser(null);
                }
            } catch (error) {
                console.error("Failed to load user", error);
                setUser(null);
            } finally {
                setLoading(false);
            }
        }

        loadUser();
    }, []);

    const login = async (_token: string) => {
        // Refetch user after successful login (cookies already set by backend)
        try {
            const response = await fetch("/api/proxy/auth/me", {
                credentials: "include",
            });
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            }
        } catch (error) {
            console.error("Failed to load user after login", error);
        }
        router.push("/");
    };

    const logout = async () => {
        try {
            await fetch("/api/proxy/auth/logout", {
                method: "POST",
                credentials: "include",
            });
            setUser(null);
            router.push("/login");
        } catch (error) {
            console.error("Logout failed", error);
        }
    };

    // Protected routes check
    useEffect(() => {
        if (!loading) {
            const publicPaths = ["/", "/login", "/signup"];

            if (!user && !publicPaths.includes(pathname)) {
                router.push("/login");
            }

            if (user && (pathname === "/login" || pathname === "/signup")) {
                router.push("/");
            }
        }
    }, [user, loading, pathname, router]);

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
