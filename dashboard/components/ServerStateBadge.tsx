"use client";

import { useEffect, useState } from 'react';
import { Server } from 'lucide-react';

type ServerState = { layerActive: boolean } | null;

export function ServerStateBadge({ initialState }: { initialState?: ServerState }) {
  const [state, setState] = useState<ServerState>(() => typeof initialState !== 'undefined' ? initialState : null);

  useEffect(() => {
    let mounted = true;
    async function fetchState() {
      try {
        const res = await fetch('/api/health');
        const json = await res.json();
        if (mounted) setState(json);
      } catch (e) {
        if (mounted) setState(null);
      }
    }
    fetchState();
    const id = setInterval(fetchState, 5000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  if (state === null) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-muted/10 rounded-full border border-muted text-muted">
        <Server className="h-4 w-4" />
        <span className="text-xs">Server: unreachable</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-full border ${state.layerActive ? 'bg-green-50 border-green-400 text-green-700' : 'bg-red-50 border-red-400 text-red-700'}`}>
      <Server className="h-4 w-4" />
      <span className="text-xs">Server: {state.layerActive ? 'Layer Active' : 'Layer Inactive'}</span>
    </div>
  );
}
