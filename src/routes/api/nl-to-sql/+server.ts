import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';

const PATSTAT_API = env.PATSTAT_API ?? 'http://127.0.0.1:52081';

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();
	const question = body?.question;
	const history = body?.history ?? [];

	if (!question || typeof question !== 'string') {
		return error(400, 'Missing or invalid "question" field');
	}

	try {
		const res = await fetch(`${PATSTAT_API}/api/nl-to-sql`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question, history })
		});

		if (!res.ok) {
			const detail = await res.json().catch(() => ({ detail: res.statusText }));
			return error(res.status, detail.detail ?? 'NL-to-SQL request failed');
		}

		// Proxy the SSE stream from sidecar to client
		return new Response(res.body, {
			headers: {
				'Content-Type': 'text/event-stream',
				'Cache-Control': 'no-cache',
				'Connection': 'keep-alive',
			}
		});
	} catch (e) {
		const message = e instanceof Error ? e.message : String(e);
		return error(502, message);
	}
};
