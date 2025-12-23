import { GlobalHealthMap } from "@/components/GlobalHealthMap";
import { SemanticLayerDemo } from "@/components/SemanticLayerDemo";
import { TrustScoreCard } from "@/components/TrustScoreCard";
import { ArrowUpRight, ShieldCheck } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-background p-8">
      {/* Header */}
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Enterprise Trust Control Center</h1>
          <p className="text-muted-foreground">Global Data Fabric & AI Reliability Monitoring</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full border border-primary/20 text-primary">
          <ShieldCheck className="h-5 w-5" />
          <span className="font-semibold text-sm">System Status: PROTECTED</span>
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
