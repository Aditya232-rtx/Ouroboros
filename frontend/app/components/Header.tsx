"use client";

import Link from "next/link";
import { Shield, Bell, Settings, User, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button } from "./lightswind/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger
} from "./lightswind/dropdown-menu";

export default function Header() {
    const { user, logout } = useAuth();
    // const pathname = usePathname();

    return (
        <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-slate-950/60">
            <div className="flex h-16 items-center px-4 sm:px-6 lg:px-8">
                <Link href="/warloop" className="flex items-center space-x-2 mr-8">
                    <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-white" />
                    </div>
                    <span className="text-lg font-bold text-slate-900 dark:text-white hidden sm:block">
                        Ouroboros
                    </span>
                </Link>

                <div className="hidden md:flex items-center space-x-1 border-l border-slate-200 dark:border-slate-800 pl-4">
                    <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                        Active Operation:
                    </span>
                    <span className="text-xs font-mono font-medium text-emerald-600 dark:text-emerald-400">
                        PROTOCOL_OMEGA
                    </span>
                </div>

                <div className="flex-1" />

                <div className="flex items-center space-x-4">
                    <Button variant="ghost" size="icon" className="relative text-slate-500 dark:text-slate-400">
                        <Bell className="h-5 w-5" />
                        <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-red-500 border-2 border-white dark:border-slate-950"></span>
                    </Button>

                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                                <div className="flex h-full w-full items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800">
                                    <User className="h-4 w-4 text-slate-600 dark:text-slate-300" />
                                </div>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-56" align="end">
                            <DropdownMenuLabel className="font-normal">
                                <div className="flex flex-col space-y-1">
                                    <p className="text-sm font-medium leading-none">{user?.full_name || "Agent"}</p>
                                    <p className="text-xs leading-none text-slate-500 dark:text-slate-400">
                                        {user?.email || "agent@ouroboros.ai"}
                                    </p>
                                </div>
                            </DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem>
                                <Settings className="mr-2 h-4 w-4" />
                                <span>Settings</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={logout} className="text-red-600 dark:text-red-400">
                                <LogOut className="mr-2 h-4 w-4" />
                                <span>Log out</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
        </header>
    );
}
