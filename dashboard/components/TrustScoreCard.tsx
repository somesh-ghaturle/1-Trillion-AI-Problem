'use client';

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ShieldCheck, AlertTriangle, XCircle } from "lucide-react";

interface TrustScoreCardProps {
    systemName: string;
    score: number;
    trend?: number; // e.g. +5.2
}

export function TrustScoreCard({ systemName, score, trend }: TrustScoreCardProps) {
    let statusColor = "text-green-500";
    let Icon = ShieldCheck;
    let statusText = "Trusted";

    if (score < 80) {
        statusColor = "text-yellow-500";
        Icon = AlertTriangle;
        statusText = "Warning";
    }
    if (score < 60) {
        statusColor = "text-red-500";
        Icon = XCircle;
        statusText = "Critical";
    }

    return (
        <Card className="border-l-4 border-l-primary/50 relative overflow-hidden group hover:border-l-primary transition-all">
            <CardHeader className="pb-2">
                <div className="flex justify-between items-center">
                    <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">{systemName}</CardTitle>
                    <Icon className={cn("h-5 w-5", statusColor)} />
                </div>
            </CardHeader>
            <CardContent>
                <div className="flex flex-col">
                    <span className={cn("text-4xl font-bold font-mono tracking-tighter", statusColor)}>
                        {score}
                    </span>
                    <div className="flex justify-between items-end mt-1">
                        <span className="text-xs text-muted-foreground">{statusText}</span>
                        {trend && (
                            <span className={cn("text-xs font-medium", trend > 0 ? "text-green-400" : "text-red-400")}>
                                {trend > 0 ? '+' : ''}{trend}%
                            </span>
                        )}
                    </div>
                </div>
                {/* Visual Bar */}
                <div className="w-full bg-secondary h-1.5 mt-4 rounded-full overflow-hidden">
                    <div
                        className={cn("h-full rounded-full transition-all duration-1000", statusColor.replace('text-', 'bg-'))}
                        style={{ width: `${score}%` }}
                    />
                </div>
            </CardContent>
        </Card>
    )
}
