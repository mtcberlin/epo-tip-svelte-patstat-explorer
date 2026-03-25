import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { queryPatstat } from '$lib/patstat';

const MAX_SQL_LENGTH = 10_000;

// Basic SQL injection prevention: only allow SELECT statements
function validateSql(sql: string): string | null {
	const trimmed = sql.trim();
	if (trimmed.length > MAX_SQL_LENGTH) return 'Query too long';
	if (!/^SELECT\b/i.test(trimmed)) return 'Only SELECT queries are allowed';
	// Block multiple statements: semicolon followed by another SQL keyword
	if (/;\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|REVOKE)\b/i.test(trimmed)) return 'Multiple statements not allowed';
	return null;
}

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json();
	const sql = body?.sql;

	if (!sql || typeof sql !== 'string') {
		return error(400, 'Missing or invalid "sql" field');
	}

	const validationError = validateSql(sql);
	if (validationError) {
		return error(400, validationError);
	}

	try {
		const rows = await queryPatstat(sql);
		return json({ rows, count: rows.length });
	} catch (e) {
		const message = e instanceof Error ? e.message : String(e);
		return error(502, message);
	}
};
