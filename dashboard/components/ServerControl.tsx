"use client";

import { useState } from 'react';

export function ServerControl({ initialState }: { initialState?: { layerActive: boolean } | null }) {
  const [loading, setLoading] = useState(false);

  const toggle = async () => {
    setLoading(true);
    try {
      // POST without payload toggles server-side state
      const res = await fetch('/api/health', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      await res.json();
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className="px-3 py-2 bg-muted/10 rounded-full border border-muted text-sm"
    >
      {loading ? 'Updating...' : 'Toggle Server Layer'}
    </button>
  );
}
