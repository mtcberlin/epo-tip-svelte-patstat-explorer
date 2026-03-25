import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';

const PATSTAT_API = env.PATSTAT_API ?? 'http://127.0.0.1:52081';

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();
	const whereClause = body?.where_clause;

	if (!whereClause || typeof whereClause !== 'string') {
		return error(400, 'Missing or invalid "where_clause" field');
	}

	try {
		const res = await fetch(`${PATSTAT_API}/api/co-occurrence`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});

		if (!res.ok) {
			const detail = await res.json().catch(() => ({ detail: res.statusText }));
			return error(res.status, detail.detail ?? 'Co-occurrence query failed');
		}

		return json(await res.json());
	} catch (e) {
		const message = e instanceof Error ? e.message : String(e);
		return error(502, message);
	}
};
