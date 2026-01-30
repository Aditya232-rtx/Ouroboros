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
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

    // Fetch current user on mount
    useEffect(() => {
        async function loadUser() {
            try {
                const response = await fetch(`${apiUrl}/auth/me`, {
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

    const login = (_token: string) => {
        // In cookie-based auth, we just need to refetch the user or set state
        // but if we receive token, we might not need to do anything if cookies are set
        // This function might be called after successful login API call
        // For now, let's reload user
        window.location.href = "/"; // Hard refresh to ensure state update or just router push
    };

    const logout = async () => {
        try {
            await fetch(`${apiUrl}/auth/logout`, {
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
