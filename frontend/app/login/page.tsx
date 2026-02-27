"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import InteractiveGridBackground from "../components/InteractiveGridBackground";
import { useAuth } from "../context/AuthContext";

function LoginForm() {
    const searchParams = useSearchParams();
    const { login } = useAuth();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const registered = searchParams.get("registered");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const response = await fetch("/api/proxy/auth/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "include",
                body: JSON.stringify({
                    email,
                    password,
                }),
            });

            if (response.ok) {
                const data = await response.json();
                // Login successful
                // AuthContext usually handles user state, but here we trigger the context login
                // data.access_token is available if we need to store it manually, 
                // but our auth.py sets httpOnly cookies.
                login(data.access_token);
            } else {
                const data = await response.json();
                setError(data.detail || "Login failed");
            }
        } catch (error) {
            console.error(error);
            setError("An error occurred. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 relative overflow-hidden">
            <InteractiveGridBackground
                gridSize={40}
                gridColor="#cbd5e1"
                darkGridColor="#1e293b"
                effectColor="rgba(59, 130, 246, 0.2)"
                darkEffectColor="rgba(59, 130, 246, 0.2)"
                className="absolute inset-0 z-0"
            />

            <div className="flex-grow flex items-center justify-center relative z-10 px-4 sm:px-6 lg:px-8">
                <div className="max-w-md w-full space-y-8 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md p-8 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800">
                    <div className="text-center">
                        <Link href="/" className="inline-flex items-center space-x-2 mb-6">
                            <span className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
                                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                </svg>
                            </span>
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">Ouroboros</span>
                        </Link>
                        <h2 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
                            Welcome back
                        </h2>
                        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                            Sign in to your account to continue
                        </p>
                    </div>

                    <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                        {registered && (
                            <div className="rounded-md bg-green-50 dark:bg-green-900/20 p-4 border border-green-200 dark:border-green-800">
                                <div className="flex">
                                    <div className="ml-3">
                                        <h3 className="text-sm font-medium text-green-800 dark:text-green-400">
                                            Registration successful! Please sign in.
                                        </h3>
                                    </div>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4 border border-red-200 dark:border-red-800">
                                <div className="flex">
                                    <div className="ml-3">
                                        <h3 className="text-sm font-medium text-red-800 dark:text-red-400">{error}</h3>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="space-y-4">
                            <div>
                                <label htmlFor="email-address" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                                    Email address
                                </label>
                                <input
                                    id="email-address"
                                    name="email"
                                    type="email"
                                    autoComplete="email"
                                    required
                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>

                            <div>
                                <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                                    Password
                                </label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    autoComplete="current-password"
                                    required
                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 dark:border-slate-700 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="flex items-center">
                                <input
                                    id="remember-me"
                                    name="remember-me"
                                    type="checkbox"
                                    className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-slate-300 rounded"
                                />
                                <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-900 dark:text-slate-300">
                                    Remember me
                                </label>
                            </div>

                            <div className="text-sm">
                                <Link href="#" className="font-medium text-emerald-600 hover:text-emerald-500">
                                    Forgot your password?
                                </Link>
                            </div>
                        </div>

                        <div>
                            <button
                                type="submit"
                                disabled={loading}
                                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
                            >
                                {loading ? (
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                ) : (
                                    <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                                        <svg className="h-5 w-5 text-emerald-500 group-hover:text-emerald-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                            <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                                        </svg>
                                    </span>
                                )}
                                {loading ? "Signing in..." : "Sign in"}
                            </button>
                        </div>
                    </form>

                    <div className="text-center">
                        <p className="mt-2 text-center text-sm text-slate-600 dark:text-slate-400">
                            Don&apos;t have an account?{" "}
                            <Link
                                href="/signup"
                                className="font-medium text-emerald-600 hover:text-emerald-500 dark:text-emerald-500 dark:hover:text-emerald-400 transition-colors"
                            >
                                Sign up
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
            <LoginForm />
        </Suspense>
    );
}