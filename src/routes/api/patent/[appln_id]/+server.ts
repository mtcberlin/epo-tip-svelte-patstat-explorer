import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';

const PATSTAT_API = env.PATSTAT_API ?? 'http://127.0.0.1:52081';

export const GET: RequestHandler = async ({ params }) => {
	const { appln_id } = params;

	if (!/^\d+$/.test(appln_id)) {
		return error(400, 'Invalid application ID');
	}

	try {
		const res = await fetch(`${PATSTAT_API}/api/patent/${appln_id}`);
		if (!res.ok) {
			const detail = await res.json().catch(() => ({ detail: res.statusText }));
			return error(res.status, detail.detail ?? 'Patent not found');
		}
		return json(await res.json());
	} catch (e) {
		const message = e instanceof Error ? e.message : String(e);
		return error(502, message);
	}
};
