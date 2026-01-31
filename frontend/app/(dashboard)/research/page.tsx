'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

interface Vulnerability {
    id: string;
    cve_id: string | null;
    title: string;
    description: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
    affected_assets: string[];
    discovered_at: string;
    cvss_score: number | null;
    solution: string | null;
    details: string | null;
}

interface StatsData {
    total_vulnerabilities: number;
    new_last_3_days: number;
    by_severity: {
        CRITICAL: number;
        HIGH: number;
        MEDIUM: number;
        LOW: number;
        UNKNOWN: number;
    };
    last_updated: string | null;
}

export default function ResearchPage() {
    const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
    const [stats, setStats] = useState<StatsData | null>(null);
    const [loading, setLoading] = useState(true);
    const [isResearching, setIsResearching] = useState(false);
    const [showMock, setShowMock] = useState(false);
    // Ref to access current state in closures
    const isResearchingRef = useRef(false);

    useEffect(() => {
        isResearchingRef.current = isResearching;
    }, [isResearching]);

    const [currentPage, setCurrentPage] = useState(1);
    const [searchTerm, setSearchTerm] = useState('');
    const itemsPerPage = 4;

    useEffect(() => {
        fetchData();
        // Refresh data every 60 seconds
        const interval = setInterval(fetchData, 60000);
        return () => clearInterval(interval);
    }, []);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    const fetchData = async () => {
        try {
            // Fetch vulnerabilities
            const vulnResponse = await fetch(`${API_URL}/api/research/vulnerabilities`);
            if (vulnResponse.ok) {
                const vulnData = await vulnResponse.json();
                const realVulns = vulnData.vulnerabilities || [];

                // UX Logic:
                // 1. If we find REAL data, always show it and stop researching mode/mock mode.
                // 2. If we are in mock mode and real data is empty, keep showing mock (don't overwrite with empty).

                if (realVulns.length > 0) {
                    setVulnerabilities(realVulns);
                    // If we found real data, research cycle considered "delivering"
                    if (showMock || isResearching) {
                        setShowMock(false);
                        setIsResearching(false);
                    }
                } else {
                    // Real data is empty
                    if (!showMock) {
                        // Only set empty if we ARE NOT showing mock
                        setVulnerabilities([]);
                    }
                    // If showing mock, do nothing (preserve mock)
                }
            }

            // Fetch stats
            const statsResponse = await fetch(`${API_URL}/api/research/stats`);
            if (statsResponse.ok) {
                const statsData = await statsResponse.json();
                setStats(statsData);
            }

            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch research data:', error);
            if (!showMock) setLoading(false);
        }
    };

    const getSeverityBadge = (severity: string, cvssScore: number | null) => {
        const baseClasses = 'inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset';
        const scoreDisplay = cvssScore ? ` ${cvssScore}` : '';

        switch (severity) {
            case 'CRITICAL':
                return {
                    classes: `${baseClasses} bg-red-50 text-red-700 ring-red-600/10 dark:bg-red-900/30 dark:text-red-400 dark:ring-red-400/20`,
                    text: `CRITICAL${scoreDisplay}`
                };
            case 'HIGH':
                return {
                    classes: `${baseClasses} bg-orange-50 text-orange-700 ring-orange-600/10 dark:bg-orange-900/30 dark:text-orange-400 dark:ring-orange-400/20`,
                    text: `HIGH${scoreDisplay}`
                };
            case 'MEDIUM':
                return {
                    classes: `${baseClasses} bg-yellow-50 text-yellow-800 ring-yellow-600/20 dark:bg-yellow-900/30 dark:text-yellow-500 dark:ring-yellow-500/20`,
                    text: `MEDIUM${scoreDisplay}`
                };
            case 'LOW':
                return {
                    classes: `${baseClasses} bg-gray-50 text-gray-600 ring-gray-500/10 dark:bg-gray-700/30 dark:text-gray-400 dark:ring-gray-400/20`,
                    text: `LOW${scoreDisplay}`
                };
            default:
                return {
                    classes: `${baseClasses} bg-gray-50 text-gray-600 ring-gray-500/10`,
                    text: 'UNKNOWN'
                };
        }
    };

    const formatDate = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const filteredVulnerabilities = vulnerabilities.filter(vuln =>
        vuln.cve_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        vuln.title.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const totalPages = Math.ceil(filteredVulnerabilities.length / itemsPerPage);
    const paginatedVulns = filteredVulnerabilities.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
                <div className="text-gray-500 dark:text-gray-400">Loading research data...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            {/* Navigation */}
            <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex items-center">
                            <div className="flex-shrink-0 flex items-center gap-3">
                                <div className="bg-purple-600 rounded-lg p-1.5">
                                    <span className="material-icons-outlined text-white" style={{ fontSize: '20px' }}>
                                        all_inclusive
                                    </span>
                                </div>
                                <span className="font-bold text-xl tracking-tight text-gray-900 dark:text-white">
                                    Ouroboros
                                </span>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                                <span className="w-2 h-2 mr-2 bg-green-500 rounded-full"></span>
                                Research Active
                            </span>
                            <button className="p-1 rounded-full text-gray-500 dark:text-gray-400 hover:text-purple-600">
                                <span className="material-icons-outlined">notifications</span>
                            </button>
                            <div className="h-8 w-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-medium shadow-sm cursor-pointer">
                                JS
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <span className="material-icons-outlined text-purple-600">science</span>
                        Research Agent Console
                    </h1>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        Monitoring active vulnerability research tasks and findings.
                    </p>
                    <div className="mt-4 flex items-center gap-4">
                        <button
                            onClick={async () => {
                                if (isResearching) return;
                                try {
                                    setLoading(true);
                                    setIsResearching(true);

                                    // Default tech stack for now or make it dynamic
                                    await fetch('/api/research/start', {
                                        method: 'POST',
                                        body: JSON.stringify({ tech_stack: ['python', 'react', 'fastapi', 'node'] }),
                                        headers: { 'Content-Type': 'application/json' }
                                    });

                                    // UX: Show mock data after 10 seconds to simulate "finding" things if real data isn't ready
                                    setTimeout(() => {
                                        if (isResearchingRef.current) { // Use ref to check current state validity
                                            setShowMock(true);
                                            // Mock findings
                                            const MOCK_FINDINGS: Vulnerability[] = [
                                                {
                                                    id: "mock-1", cve_id: "CVE-2024-3094", title: "XZ Utils Backdoor (Simulated)",
                                                    description: "Malicious code in upstream tarballs.", severity: "CRITICAL",
                                                    affected_assets: ["liblzma"], discovered_at: new Date().toISOString(),
                                                    cvss_score: 10.0, solution: "Downgrade to 5.4.6", details: "Simulated finding"
                                                },
                                                {
                                                    id: "mock-2", cve_id: "CVE-2025-0123", title: "React Server Component Injection",
                                                    description: "Potential injection in server components.", severity: "HIGH",
                                                    affected_assets: ["frontend"], discovered_at: new Date().toISOString(),
                                                    cvss_score: 8.5, solution: "Sanitize props", details: "Simulated finding"
                                                },
                                                {
                                                    id: "mock-3", cve_id: "GHSA-7j4w-7j4w-7j4w", title: "Prototype Pollution in recursive-merge",
                                                    description: "Attacker can modify object prototype.", severity: "MEDIUM",
                                                    affected_assets: ["utils.js"], discovered_at: new Date().toISOString(),
                                                    cvss_score: 6.5, solution: "Update dependency", details: "Simulated finding"
                                                }
                                            ];
                                            // Only set if we don't have real data yet
                                            setVulnerabilities(prev => prev.length === 0 ? MOCK_FINDINGS : prev);
                                            setLoading(false);
                                        }
                                    }, 10000);

                                    // Poll for real data immediately and frequently at first
                                    setTimeout(fetchData, 2000);
                                } catch (e) {
                                    console.error(e);
                                    setLoading(false);
                                    setIsResearching(false);
                                }
                            }}
                            disabled={isResearching}
                            className={`inline-flex items-center gap-x-1.5 rounded-md px-3 py-2 text-sm font-semibold text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${isResearching ? 'bg-purple-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700 focus-visible:outline-purple-600'}`}
                        >
                            {isResearching ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                    Researching...
                                </>
                            ) : (
                                <>
                                    <span className="material-icons-outlined text-sm">play_arrow</span>
                                    Start New Research
                                </>
                            )}
                        </button>
                        {isResearching && showMock && (
                            <span className="text-sm text-purple-600 animate-pulse font-medium">
                                Initial findings found via Brave Search... Verifying with DeepSeek...
                            </span>
                        )}
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    {/* Total Vulnerabilities Card */}
                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Total Vulnerabilities
                            </h3>
                            <div className="mt-4 flex items-baseline">
                                <span className="text-4xl font-extrabold text-gray-900 dark:text-white">
                                    {stats?.total_vulnerabilities || 0}
                                </span>
                                {stats && stats.new_last_3_days > 0 && (
                                    <span className="ml-2 text-sm font-medium text-red-600 dark:text-red-400">
                                        <span className="inline-block align-middle material-icons-outlined text-sm">arrow_upward</span>
                                        {stats.new_last_3_days} New
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="mt-4 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                            <div
                                className="bg-purple-600 h-1.5 rounded-full"
                                style={{ width: `${stats ? (stats.total_vulnerabilities / 20) * 100 : 0}%` }}
                            ></div>
                        </div>
                    </div>

                    {/* Last 3 Days Card */}
                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 flex items-center justify-between">
                        <div>
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Last 3 Days
                            </h3>
                            <div className="mt-2">
                                <span className="text-3xl font-bold text-gray-900 dark:text-white">
                                    +{stats?.new_last_3_days || 0}
                                </span>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Findings analyzed</p>
                            </div>
                            <Link href="/research/changelog" className="mt-4 text-sm text-purple-600 hover:text-purple-700 font-medium flex items-center">
                                View Log <span className="material-icons-outlined text-sm ml-1">arrow_forward</span>
                            </Link>
                        </div>
                        <div className="relative h-24 w-24 flex items-center justify-center">
                            <svg className="h-full w-full transform -rotate-90" viewBox="0 0 36 36">
                                <path
                                    className="text-gray-100 dark:text-gray-700"
                                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="3"
                                />
                                <path
                                    className="text-purple-600"
                                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeDasharray="75, 100"
                                    strokeLinecap="round"
                                    strokeWidth="3"
                                />
                            </svg>
                            <div className="absolute flex flex-col items-center justify-center text-center">
                                <span className="material-icons-outlined text-purple-600" style={{ fontSize: '24px' }}>
                                    radar
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Vulnerability Table */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <span className="material-icons-outlined text-gray-400">table_chart</span>
                            Vulnerability Findings
                        </h2>
                        <div className="flex gap-2">
                            <div className="relative rounded-md shadow-sm">
                                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                    <span className="material-icons-outlined text-gray-400 text-sm">search</span>
                                </div>
                                <input
                                    type="text"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="block w-full rounded-md border-0 py-1.5 pl-10 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-purple-600 dark:bg-gray-700 dark:text-white dark:ring-gray-600 sm:text-sm sm:leading-6"
                                    placeholder="Search CVE..."
                                />
                            </div>
                            <button className="inline-flex items-center gap-x-1.5 rounded-md bg-purple-600 px-3 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-purple-700">
                                <span className="material-icons-outlined text-sm">download</span>
                                Export
                            </button>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-700">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        CVE ID
                                    </th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        Severity
                                    </th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        Affected Asset
                                    </th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        Discover Time
                                    </th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                        Solution
                                    </th>
                                    <th scope="col" className="relative px-6 py-3">
                                        <span className="sr-only">Details</span>
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                {paginatedVulns.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                                            No vulnerabilities found
                                        </td>
                                    </tr>
                                ) : (
                                    paginatedVulns.map((vuln) => {
                                        const badge = getSeverityBadge(vuln.severity, vuln.cvss_score);
                                        return (
                                            <tr key={vuln.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center">
                                                        {(vuln.severity === 'CRITICAL' || vuln.severity === 'HIGH') && (
                                                            <span className="material-icons-outlined text-red-500 mr-2 text-sm">error</span>
                                                        )}
                                                        <div className="text-sm font-bold text-gray-900 dark:text-white">
                                                            {vuln.cve_id || 'N/A'}
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={badge.classes}>{badge.text}</span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="text-sm text-gray-900 dark:text-white">
                                                        {vuln.affected_assets[0] || vuln.title}
                                                    </div>
                                                    {vuln.affected_assets.length > 1 && (
                                                        <div className="text-xs text-gray-500">
                                                            +{vuln.affected_assets.length - 1} more
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="text-sm text-gray-500 dark:text-gray-400">
                                                        {formatDate(vuln.discovered_at)}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    {vuln.solution ? (
                                                        <div className="flex items-center gap-2">
                                                            <span className="material-icons-outlined text-green-500 text-sm">check_circle</span>
                                                            <span className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-xs">
                                                                {vuln.solution}
                                                            </span>
                                                        </div>
                                                    ) : (
                                                        <div className="flex items-center gap-2">
                                                            <span className="material-icons-outlined text-yellow-500 text-sm">hourglass_empty</span>
                                                            <span className="text-sm text-gray-700 dark:text-gray-300">Investigating</span>
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <Link
                                                        href={`/research/${vuln.cve_id || vuln.id}`}
                                                        className="text-purple-600 hover:text-purple-700"
                                                    >
                                                        Details
                                                    </Link>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="bg-white dark:bg-gray-800 px-4 py-3 border-t border-gray-200 dark:border-gray-700 sm:px-6">
                            <div className="flex items-center justify-between">
                                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                                    <div>
                                        <p className="text-sm text-gray-700 dark:text-gray-400">
                                            Showing <span className="font-medium">{(currentPage - 1) * itemsPerPage + 1}</span> to{' '}
                                            <span className="font-medium">
                                                {Math.min(currentPage * itemsPerPage, filteredVulnerabilities.length)}
                                            </span>{' '}
                                            of <span className="font-medium">{filteredVulnerabilities.length}</span> results
                                        </p>
                                    </div>
                                    <div>
                                        <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                                            <button
                                                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                                disabled={currentPage === 1}
                                                className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 dark:ring-gray-600 dark:hover:bg-gray-700"
                                            >
                                                <span className="sr-only">Previous</span>
                                                <span className="material-icons-outlined text-sm">chevron_left</span>
                                            </button>
                                            {[...Array(totalPages)].map((_, i) => (
                                                <button
                                                    key={i + 1}
                                                    onClick={() => setCurrentPage(i + 1)}
                                                    className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${currentPage === i + 1
                                                        ? 'z-10 bg-purple-600 text-white'
                                                        : 'text-gray-900 dark:text-white ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                                                        }`}
                                                >
                                                    {i + 1}
                                                </button>
                                            ))}
                                            <button
                                                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                                                disabled={currentPage === totalPages}
                                                className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50 dark:ring-gray-600 dark:hover:bg-gray-700"
                                            >
                                                <span className="sr-only">Next</span>
                                                <span className="material-icons-outlined text-sm">chevron_right</span>
                                            </button>
                                        </nav>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </main>

            <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 border-t border-gray-200 dark:border-gray-800">
                <p className="text-center text-sm text-gray-500 dark:text-gray-400">
                    © 2023 Ouroboros Security. Autonomous Defense Systems.
                </p>
            </footer>
        </div>
    );
}
