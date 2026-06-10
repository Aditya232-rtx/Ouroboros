"use client";

import { Button } from "./lightswind/button";
import { Check, X, FileCode } from "lucide-react";

interface PatchPreviewProps {
    file: string;
    diff: string;
    onApprove?: () => void;
    onReject?: () => void;
    className?: string;
}

export default function PatchPreview({ file, diff, onApprove, onReject, className = "" }: PatchPreviewProps) {
    // Basic line number logic (just counting lines for demo)
    const lines = diff.split('\n');

    return (
        <div className={`font-mono text-sm ${className}`}>
            {/* If buttons exist, show a minimal toolbar, otherwise hidden since parent has header */}
            {(onApprove || onReject) && (
                <div className="flex items-center justify-end px-4 py-2 border-b border-slate-800 bg-slate-900/50">
                    <div className="flex items-center space-x-2">
                        {onReject && (
                            <Button size="sm" variant="ghost" onClick={onReject} className="text-red-400 hover:text-red-300 hover:bg-red-900/20">
                                <X className="h-4 w-4 mr-1" /> Reject
                            </Button>
                        )}
                        {onApprove && (
                            <Button size="sm" onClick={onApprove} className="bg-emerald-600 hover:bg-emerald-500 text-white border-0">
                                <Check className="h-4 w-4 mr-1" /> Approve Fix
                            </Button>
                        )}
                    </div>
                </div>
            )}

            <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                    <tbody>
                        {lines.map((line, i) => {
                            // Simple heuristic for line numbers: start at 43 based on dummyDiff
                            const lineNumber = 43 + i;
                            const isAdd = line.startsWith('+');
                            const isDel = line.startsWith('-');
                            const isHeader = line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++');

                            if (isHeader) {
                                return (
                                    <tr key={i} className="bg-[#161b22] text-slate-500">
                                        <td className="w-12 px-4 py-0.5 text-right select-none text-[10px] opacity-0">.</td>
                                        <td className="px-4 py-0.5 w-full whitespace-pre">{line}</td>
                                    </tr>
                                )
                            }

                            return (
                                <tr key={i} className={`
                                    ${isAdd ? 'bg-[#2ea043]/15' : ''}
                                    ${isDel ? 'bg-[#da3633]/15' : ''}
                                `}>
                                    <td className="w-12 px-3 py-0.5 text-right select-none text-slate-600 border-r border-slate-800 bg-[#0d1117] text-xs align-top pt-1">
                                        {lineNumber}
                                    </td>
                                    <td className={`px-4 py-0.5 w-full whitespace-pre align-top text-slate-300 ${isAdd ? 'text-[#e6edf3]' : ''} ${isDel ? 'text-[#e6edf3]' : ''}`}>
                                        <div className="flex">
                                            <span className={`w-4 inline-block select-none ${isAdd ? 'text-[#3fb950]' : ''} ${isDel ? 'text-[#f85149]' : ''}`}>
                                                {isAdd ? '+' : isDel ? '-' : ' '}
                                            </span>
                                            <span>
                                                {/* Highlight the changed part if possible, simpler for now */}
                                                {line.substring(1)}
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
