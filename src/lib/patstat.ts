import { env } from '$env/dynamic/private';

const PATSTAT_API = env.PATSTAT_API ?? 'http://127.0.0.1:52081';

export async function queryPatstat(sql: string): Promise<Record<string, unknown>[]> {
	const res = await fetch(`${PATSTAT_API}/api/query`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ sql })
	});

	if (!res.ok) {
		const text = await res.text();
		throw new Error(`PATSTAT query failed (${res.status}): ${text}`);
	}

	return res.json();
}

export async function healthCheck(): Promise<{ ok: boolean; message: string }> {
	try {
		const res = await fetch(`${PATSTAT_API}/api/health`);
		if (!res.ok) throw new Error(`Status ${res.status}`);
		return res.json();
	} catch (e) {
		return { ok: false, message: `Sidecar unreachable: ${e}` };
	}
}
