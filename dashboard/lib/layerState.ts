import fs from 'fs';
import path from 'path';
import Redis from 'ioredis';

const DEFAULT_FILE = path.resolve(process.cwd(), 'layer_state.json');
const STATE_KEY = 'semantic_layer:active';

let redisClient: Redis | null = null;

function getStateFile(): string {
  return process.env.LAYER_STATE_FILE || DEFAULT_FILE;
}

function readStateFromFile(): boolean | null {
  try {
    const raw = fs.readFileSync(getStateFile(), 'utf-8');
    const parsed = JSON.parse(raw);
    return typeof parsed.layerActive === 'boolean' ? parsed.layerActive : null;
  } catch (e) {
    return null;
  }
}

function writeStateToFile(v: boolean) {
  try {
    fs.writeFileSync(getStateFile(), JSON.stringify({ layerActive: v }, null, 2));
    return true;
  } catch (e) {
    return false;
  }
}

function getRedisClient(): Redis | null {
  if (redisClient) return redisClient;
  const url = process.env.REDIS_URL;
  if (!url) return null;
  redisClient = new Redis(url);
  redisClient.on('error', (e) => console.error('Redis error', e));
  return redisClient;
}

export async function getLayerState(): Promise<boolean> {
  // Priority: env var > Redis > file fallback > default true
  const env = process.env.SEMANTIC_LAYER_ACTIVE;
  if (typeof env !== 'undefined') return env === 'true' || env === '1';

  const client = getRedisClient();
  if (client) {
    try {
      const v = await client.get(STATE_KEY);
      if (v === '1' || v === '0') return v === '1';
    } catch (e) {
      console.error('Redis read failed', e);
    }
  }

  const fromFile = readStateFromFile();
  if (typeof fromFile === 'boolean') return fromFile;
  return true;
}

export async function setLayerState(v: boolean): Promise<boolean> {
  const client = getRedisClient();
  let ok = false;
  if (client) {
    try {
      await client.set(STATE_KEY, v ? '1' : '0');
      ok = true;
    } catch (e) {
      console.error('Redis write failed', e);
      ok = false;
    }
  }
  // best-effort file persistence as fallback/replica
  const fileOk = writeStateToFile(v);
  return ok || fileOk;
}
