import fs from 'fs';
import path from 'path';
import { GlobalHealthMap } from "@/components/GlobalHealthMap";
import { SemanticLayerDemo } from "@/components/SemanticLayerDemo";
import { TrustScoreCard } from "@/components/TrustScoreCard";
import { ArrowUpRight, ShieldCheck } from "lucide-react";
import { ServerStateBadge } from "@/components/ServerStateBadge";
import { ServerControl } from "@/components/ServerControl";

export default function Home() {
  // Server-side read of persisted layer state for SSR fallback
  let serverState: { layerActive: boolean } | null = null;
  try {
    const statePath = path.resolve(process.cwd(), 'layer_state.json');
    const raw = fs.readFileSync(statePath, 'utf-8');
    const parsed = JSON.parse(raw);
    serverState = typeof parsed.layerActive === 'boolean' ? { layerActive: parsed.layerActive } : null;
  } catch (e) {
    // If state file is missing or read fails, default to true (matches API behavior)
    serverState = { layerActive: true };
  }

  return (
    <main className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Enterprise Trust Control Center</h1>
          <p className="text-muted-foreground">Global Data Fabric & AI Reliability Monitoring</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full border border-primary/20 text-primary">
            <ShieldCheck className="h-5 w-5" />
            <span className="font-semibold text-sm">System Status: PROTECTED</span>
          </div>

          {/* Server-side badge fallback (SSR) */}
          {serverState === null ? (
            <div className="flex items-center gap-2 px-3 py-2 bg-muted/10 rounded-full border border-muted text-muted">
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 7h18M3 12h18M3 17h18" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
              <span className="text-xs">Server: unreachable</span>
            </div>
          ) : (
            <div className={`flex items-center gap-2 px-3 py-2 rounded-full border ${serverState.layerActive ? 'bg-green-50 border-green-400 text-green-700' : 'bg-red-50 border-red-400 text-red-700'}`}>
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2v20M2 12h20" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
              <span className="text-xs">Server: {serverState.layerActive ? 'Layer Active' : 'Layer Inactive'}</span>
            </div>
          )}

          {/* Client badge for live updates */}
          <ServerStateBadge initialState={serverState} />
          <ServerControl initialState={serverState} />
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* Left Column: Metrics & Health */}
        <div className="lg:col-span-4 space-y-8">

          {/* Score Cards */}
          <div className="space-y-4">
            <h2 className="text-sm uppercase tracking-wider text-muted-foreground font-semibold">Trust Scores</h2>
            <div className="grid grid-cols-1 gap-4">
              <TrustScoreCard systemName="Global AI Readiness" score={68} trend={-2.4} />
              <div className="grid grid-cols-2 gap-4">
                <TrustScoreCard systemName="Snowflake" score={98} trend={1.2} />
                <TrustScoreCard systemName="Tableau" score={42} trend={-5.1} />
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="p-6 rounded-xl border bg-card/50 backdrop-blur">
            <h3 className="font-semibold mb-4">Recommended Actions</h3>
            <ul className="space-y-3 text-sm">
              <li className="flex items-center justify-between p-2 rounded hover:bg-muted cursor-pointer transition-colors group">
                <span className="text-red-400">Fix Schema Drift in Salesforce</span>
                <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </li>
              <li className="flex items-center justify-between p-2 rounded hover:bg-muted cursor-pointer transition-colors group">
                <span>Approve new Metrics Dictionary</span>
                <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
              </li>
            </ul>
          </div>

        </div>

        {/* Right Column: Visualization & Interactive Demo */}
        <div className="lg:col-span-8 space-y-8">

          {/* Interactive Semantic Layer */}
          <SemanticLayerDemo />

          {/* Network Graph */}
          <GlobalHealthMap />

        </div>

      </div>
    </main>
  )
}
