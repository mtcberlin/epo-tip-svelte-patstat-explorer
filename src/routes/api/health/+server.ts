import { json } from '@sveltejs/kit';
import { healthCheck } from '$lib/patstat';

export async function GET() {
	const status = await healthCheck();
	return json(status, { status: status.ok ? 200 : 503 });
}
