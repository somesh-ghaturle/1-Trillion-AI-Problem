import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

// Ensure environment isolation for tests
const TMP_FILE = path.resolve(process.cwd(), 'layer_state.test.json');

beforeEach(() => {
  process.env.REDIS_URL = '';
  process.env.LAYER_STATE_FILE = TMP_FILE;
  delete process.env.SEMANTIC_LAYER_ACTIVE;
  if (fs.existsSync(TMP_FILE)) fs.unlinkSync(TMP_FILE);
});

afterEach(() => {
  if (fs.existsSync(TMP_FILE)) fs.unlinkSync(TMP_FILE);
  delete process.env.LAYER_STATE_FILE;
});

describe('layerState file fallback', () => {
  it('returns default true when no file or env', async () => {
    const mod = await import('../layerState');
    const v = await mod.getLayerState();
    expect(v).toBe(true);
  });

  it('persists and reads state via file fallback', async () => {
    const mod = await import('../layerState');
    const ok = await mod.setLayerState(false);
    expect(ok).toBe(true);
    const v = await mod.getLayerState();
    expect(v).toBe(false);
  });

  it('honors SEMANTIC_LAYER_ACTIVE env override', async () => {
    process.env.SEMANTIC_LAYER_ACTIVE = '0';
    const mod = await import('../layerState');
    const v = await mod.getLayerState();
    expect(v).toBe(false);
  });
});
