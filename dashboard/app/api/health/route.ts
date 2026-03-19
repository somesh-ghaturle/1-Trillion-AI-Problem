import { NextResponse } from 'next/server';
import { getLayerState, setLayerState } from '../../../lib/layerState';

// Basic in-memory rate limiter (per-ip) for demo.
const RATE_LIMIT_WINDOW_MS = 60_000; // 1 minute
const RATE_LIMIT_MAX = 30; // max requests per window per IP
const ipRequests = new Map<string, number[]>();

function getIp(req: Request) {
  try {
    // Next.js Request exposes headers via request.headers
    // Prefer x-forwarded-for if present
    const h = (req as any).headers;
    if (h) {
      const xf = h.get && h.get('x-forwarded-for');
      if (xf) return xf.split(',')[0].trim();
      const ip = h.get && h.get('x-real-ip');
      if (ip) return ip;
    }
  } catch (e) {
    // ignore
  }
  return 'local';
}

function isRateLimited(ip: string) {
  const now = Date.now();
  const arr = ipRequests.get(ip) || [];
  const kept = arr.filter((t) => now - t < RATE_LIMIT_WINDOW_MS);
  kept.push(now);
  ipRequests.set(ip, kept);
  return kept.length > RATE_LIMIT_MAX;
}

function requireAuth(req: Request) {
  const expected = process.env.ADMIN_TOKEN;
  if (!expected) return true; // no auth configured in env — allow for local/dev
  try {
    const h = (req as any).headers;
    const auth = h && h.get && h.get('authorization');
    if (!auth) return false;
    const parts = auth.split(' ');
    if (parts.length !== 2) return false;
    const token = parts[1];
    return token === expected;
  } catch (e) {
    return false;
  }
}

export async function GET(request: Request) {
  const ip = getIp(request);
  if (isRateLimited(ip)) {
    return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
  }
  const layerActive = await getLayerState();
  return NextResponse.json({ layerActive });
}

export async function POST(request: Request) {
  const ip = getIp(request);
  if (isRateLimited(ip)) {
    return NextResponse.json({ error: 'rate_limited' }, { status: 429 });
  }
  if (!requireAuth(request)) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json();
    if (typeof body.layerActive === 'boolean') {
      const ok = await setLayerState(body.layerActive);
      return NextResponse.json({ layerActive: body.layerActive, persisted: ok });
    }
    // support toggle without explicit payload
    if (body && Object.keys(body).length === 0) {
      const current = await getLayerState();
      const next = !current;
      const ok = await setLayerState(next);
      return NextResponse.json({ layerActive: next, persisted: ok });
    }
    return NextResponse.json({ error: 'invalid payload' }, { status: 400 });
  } catch (e) {
    return NextResponse.json({ error: 'invalid json' }, { status: 400 });
  }
}
