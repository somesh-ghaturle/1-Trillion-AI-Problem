'use client';

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const NODES = [
    { id: 'snowflake', label: 'Snowflake', x: 20, y: 50, type: 'source', status: 'healthy' },
    { id: 'salesforce', label: 'Salesforce', x: 20, y: 20, type: 'source', status: 'warning' },
    { id: 'tableau', label: 'Tableau', x: 80, y: 20, type: 'consumer', status: 'warning' },
    { id: 'ai_model', label: 'Churn Model', x: 80, y: 50, type: 'consumer', status: 'critical' },
    { id: 'marketing', label: 'Marketing App', x: 80, y: 80, type: 'consumer', status: 'healthy' },
    // The Central Fabric
    { id: 'fabric', label: 'Trust Fabric', x: 50, y: 50, type: 'fabric', status: 'healthy' },
];

export function GlobalHealthMap() {
    return (
        <Card className="min-h-[400px] relative overflow-hidden bg-dot-pattern">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-background/80 via-background to-background pointer-events-none" />
            <CardHeader className="relative z-10">
                <CardTitle>Global Data Estate Map</CardTitle>
            </CardHeader>
            <CardContent className="h-[350px] relative z-10">
                <div className="relative w-full h-full">
                    {/* Lines */}
                    <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                        <line x1="22" y1="52" x2="48" y2="52" className="stroke-primary/30" strokeWidth="0.5" />
                        <line x1="22" y1="25" x2="48" y2="50" className="stroke-yellow-500/40" strokeWidth="0.5" strokeDasharray="2,2" />
                        <line x1="52" y1="50" x2="78" y2="25" className="stroke-yellow-500/40" strokeWidth="0.5" strokeDasharray="2,2" />
                        <line x1="52" y1="50" x2="78" y2="50" className="stroke-red-500/40" strokeWidth="0.5" strokeDasharray="2,2" />
                        <line x1="52" y1="50" x2="78" y2="75" className="stroke-primary/30" strokeWidth="0.5" />
                    </svg>

                    {NODES.map((node) => (
                        <div
                            key={node.id}
                            className={cn(
                                "absolute w-24 h-24 -ml-12 -mt-12 flex flex-col items-center justify-center rounded-2xl border-2 bg-card shadow-xl transition-all hover:scale-105 cursor-pointer backdrop-blur-sm",
                                node.type === 'fabric' ? "w-32 h-32 -ml-16 -mt-16 border-primary bg-primary/5 z-20" : "z-10",
                                node.status === 'critical' ? "border-red-500/50 shadow-red-500/20" :
                                    node.status === 'warning' ? "border-yellow-500/50 shadow-yellow-500/20" :
                                        "border-border"
                            )}
                            style={{ left: `${node.x}%`, top: `${node.y}%` }}
                        >
                            <div className={cn(
                                "w-3 h-3 rounded-full mb-2 animate-pulse",
                                node.status === 'healthy' ? "bg-green-500" :
                                    node.status === 'warning' ? "bg-yellow-500" : "bg-red-500"
                            )} />
                            <span className="text-xs font-semibold text-center">{node.label}</span>
                            {node.type === 'fabric' && <span className="text-[10px] text-primary mt-1">Active</span>}
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}
