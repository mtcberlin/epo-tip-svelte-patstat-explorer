import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';

const PATSTAT_API = env.PATSTAT_API ?? 'http://127.0.0.1:52081';

export const GET: RequestHandler = async () => {
	try {
		const res = await fetch(`${PATSTAT_API}/api/settings`);
		if (!res.ok) return error(502, 'Failed to load settings');
		return json(await res.json());
	} catch (e) {
		return error(502, e instanceof Error ? e.message : String(e));
	}
};

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();

	try {
		const res = await fetch(`${PATSTAT_API}/api/settings`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		if (!res.ok) return error(502, 'Failed to save settings');
		return json(await res.json());
	} catch (e) {
		return error(502, e instanceof Error ? e.message : String(e));
	}
};
