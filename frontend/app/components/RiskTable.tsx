"use client";

import { Vulnerability } from "../lib/types";
import { Badge } from "./lightswind/badge";
import { Button } from "./lightswind/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./lightswind/table";
import { ShieldAlert, AlertTriangle, AlertCircle, Info, ChevronRight } from "lucide-react";

interface RiskTableProps {
    vulnerabilities: Vulnerability[];
}

export default function RiskTable({ vulnerabilities }: RiskTableProps) {
    const getSeverityIcon = (severity: string) => {
        switch (severity) {
            case "critical": return <ShieldAlert className="h-4 w-4 text-red-500" />;
            case "high": return <AlertTriangle className="h-4 w-4 text-orange-500" />;
            case "medium": return <AlertCircle className="h-4 w-4 text-yellow-500" />;
            default: return <Info className="h-4 w-4 text-blue-500" />;
        }
    };

    const getSeverityBadge = (severity: string) => {
        switch (severity) {
            case "critical": return <Badge variant="destructive" className="bg-red-500/10 text-red-600 border-red-200">Critical</Badge>;
            case "high": return <Badge variant="default" className="bg-orange-500/10 text-orange-600 border-orange-200 hover:bg-orange-500/20">High</Badge>;
            case "medium": return <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-600 border-yellow-200">Medium</Badge>;
            case "low": return <Badge variant="outline" className="text-blue-600 border-blue-200">Low</Badge>;
            default: return <Badge variant="outline">Unknown</Badge>;
        }
    };

    return (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-[100px]">Severity</TableHead>
                        <TableHead>Vulnerability</TableHead>
                        <TableHead>Location</TableHead>
                        <TableHead>Date Found</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {vulnerabilities.map((vuln) => (
                        <TableRow key={vuln.id} className="group hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                            <TableCell className="font-medium">
                                <div className="flex items-center space-x-2">
                                    {getSeverityIcon(vuln.severity)}
                                    <span className="capitalize hidden sm:inline">{vuln.severity}</span>
                                </div>
                            </TableCell>
                            <TableCell>
                                <div className="flex flex-col">
                                    <span className="font-semibold text-slate-900 dark:text-slate-100">{vuln.title}</span>
                                    <span className="text-xs text-slate-500 line-clamp-1">{vuln.description}</span>
                                </div>
                            </TableCell>
                            <TableCell>
                                <code className="text-xs font-mono bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-slate-600 dark:text-slate-400">
                                    {vuln.file_path}:{vuln.line_number}
                                </code>
                            </TableCell>
                            <TableCell className="text-slate-500 text-sm">
                                {new Date(vuln.date_found).toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                                <Badge variant={vuln.status === "open" ? "destructive" : "outline"}>
                                    {vuln.status}
                                </Badge>
                            </TableCell>
                            <TableCell className="text-right">
                                <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                                    Details <ChevronRight className="ml-1 h-3 w-3" />
                                </Button>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
