'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, Database, Layers, CheckCircle2, AlertOctagon } from "lucide-react";
import { cn } from "@/lib/utils";

// Mock Data
type SourceData = {
    revenue: number;
    currency: string;
    status: string;
};

type RawData = Record<'snowflake' | 'tableau' | 'salesforce', SourceData>;

const RAW_DATA: RawData = {
    snowflake: { revenue: 104502.5, currency: "USD", status: "unverified" },
    tableau: { revenue: 105000, currency: "USD", status: "estimated" },
    salesforce: { revenue: 104502, currency: "USD", status: "closed_won" }
};

const SEMANTIC_DATA = {
    revenue: 104502.5,
    currency: "USD",
    definition: "SUM(transaction_amount) WHERE status = 'closed_won'",
    source_of_truth: "Snowflake (Verified)"
};

export function SemanticLayerDemo() {
    const [isEnabled, setIsEnabled] = useState<boolean>(() => {
        try {
            const v = localStorage.getItem('semanticLayerActive');
            return v === null ? true : v === 'true';
        } catch (e) {
            return true;
        }
    });

    // Sync initial client localStorage on mount (guards SSR)
    useEffect(() => {
        try {
            const v = localStorage.getItem('semanticLayerActive');
            if (v === null) localStorage.setItem('semanticLayerActive', String(isEnabled));
        } catch (e) {}
    }, []);

    const toggleLayer = async () => {
        const next = !isEnabled;
        setIsEnabled(next);
        try { localStorage.setItem('semanticLayerActive', String(next)); } catch (e) {}
        // Try to persist server-side as well (best-effort)
        try {
            await fetch('/api/health', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ layerActive: next })
            });
        } catch (e) {
            // ignore network errors
        }
    };

    return (
        <Card className="col-span-1 md:col-span-2 border-primary/20 bg-gradient-to-br from-card to-secondary/30">
            <CardHeader>
                <div className="flex justify-between items-center">
                    <div>
                        <CardTitle className="text-xl">Semantic Layer Simulator</CardTitle>
                        <CardDescription>Toggle the layer to resolve data inconsistencies across the enterprise.</CardDescription>
                    </div>
                    <Button
                        variant={isEnabled ? "default" : "outline"}
                        onClick={toggleLayer}
                        className={cn("w-40 transition-all", isEnabled ? "bg-primary hover:bg-primary/90" : "")}
                    >
                        {isEnabled ? "Layer Active" : "Layer Inactive"}
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">

                    {/* Left: Improving Entropy */}
                    <div className="space-y-4">
                        <div className="text-xs font-semibold uppercase text-muted-foreground tracking-wider mb-2">Data Sources (Silos)</div>
                        {(['snowflake', 'tableau', 'salesforce'] as const).map((source) => (
                            <div key={source} className={cn(
                                "p-3 rounded-lg border text-sm transition-all duration-500",
                                isEnabled ? "opacity-50 grayscale" : "bg-card shadow-sm"
                            )}>
                                <div className="flex items-center gap-2 mb-1">
                                    <Database className="h-3 w-3" />
                                    <span className="font-semibold capitalize">{source}</span>
                                </div>
                                <div className="font-mono text-xs">
                                    Rev: ${RAW_DATA[source].revenue.toLocaleString()}
                                </div>
                                {!isEnabled && (
                                    <div className="text-[10px] text-red-500 flex items-center gap-1 mt-1">
                                        <AlertOctagon className="h-3 w-3" /> Inconsistent
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Middle: The Transformation */}
                    <div className="flex flex-col items-center justify-center space-y-2 text-center">
                        <div className={cn(
                            "h-16 w-16 rounded-full flex items-center justify-center transition-all duration-500 border-2",
                            isEnabled ? "bg-primary text-primary-foreground border-primary shadow-[0_0_30px_rgba(59,130,246,0.5)]" : "bg-muted text-muted-foreground border-border"
                        )}>
                            <Layers className="h-8 w-8" />
                        </div>
                        <div className="text-xs font-medium text-muted-foreground">
                            {isEnabled ? "Semantic Governance Applied" : "Direct Point-to-Point Chaos"}
                        </div>
                        <ArrowRight className={cn("h-6 w-6 transition-all duration-500", isEnabled ? "text-primary" : "text-muted-foreground/30")} />
                    </div>

                    {/* Right: The Consumer */}
                    <div className="h-full">
                        <div className="text-xs font-semibold uppercase text-muted-foreground tracking-wider mb-2">AI Consumer</div>
                        <div className={cn(
                            "h-full min-h-[160px] rounded-xl border-2 p-6 flex flex-col justify-center transition-all duration-500",
                            isEnabled ? "border-green-500/50 bg-green-500/10" : "border-red-500/20 bg-red-500/5"
                        )}>
                            <div className="text-sm font-medium mb-2">Total Revenue Input</div>
                            <div className={cn(
                                "text-3xl font-bold font-mono tracking-tight transition-all",
                                isEnabled ? "text-green-500 dark:text-green-400" : "text-red-500 dark:text-red-400"
                            )}>
                                ${isEnabled ? SEMANTIC_DATA.revenue.toLocaleString() : "???"}
                            </div>

                            <div className="mt-4 flex items-center gap-2 text-sm">
                                {isEnabled ? (
                                    <>
                                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                                        <span className="text-green-600 dark:text-green-400">Trust Score: 100/100</span>
                                    </>
                                ) : (
                                    <>
                                        <AlertOctagon className="h-4 w-4 text-red-500" />
                                        <span className="text-red-600 dark:text-red-400">Trust Score: 42/100</span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>

                </div>
            </CardContent>
        </Card>
    )
}
