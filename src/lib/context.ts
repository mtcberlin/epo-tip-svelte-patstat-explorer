/**
 * Shared analysis context — passed via URL search params across views.
 * Keeps links shareable and avoids app-level state.
 */

export interface AnalysisContext {
	names: string[];
	label: string;
	cpc?: string;
	from?: number;
	to?: number;
}

/** Parse analysis context from URLSearchParams. */
export function parseContext(params: URLSearchParams): AnalysisContext {
	const namesRaw = params.get('names') ?? params.get('name') ?? '';
	const names = namesRaw.includes('|||')
		? namesRaw.split('|||').filter(Boolean)
		: namesRaw ? [namesRaw] : [];

	return {
		names,
		label: params.get('label') ?? names[0] ?? '',
		cpc: params.get('cpc') || undefined,
		from: params.has('from') ? Number(params.get('from')) : undefined,
		to: params.has('to') ? Number(params.get('to')) : undefined,
	};
}

/** Build URL search params string from context. */
export function contextToParams(ctx: AnalysisContext): string {
	const p = new URLSearchParams();
	if (ctx.names.length === 1) {
		p.set('name', ctx.names[0]);
	} else if (ctx.names.length > 1) {
		p.set('names', ctx.names.join('|||'));
	}
	if (ctx.label && ctx.label !== ctx.names[0]) p.set('label', ctx.label);
	if (ctx.cpc) p.set('cpc', ctx.cpc);
	if (ctx.from) p.set('from', String(ctx.from));
	if (ctx.to) p.set('to', String(ctx.to));
	return p.toString();
}

/** Build SQL WHERE clause for the name(s) in context. */
export function nameWhereClause(ctx: AnalysisContext, personAlias = 'p'): string {
	if (ctx.names.length === 0) return '1=0';
	if (ctx.names.length === 1) {
		return `${personAlias}.person_name = '${ctx.names[0].replace(/'/g, "''")}'`;
	}
	const inList = ctx.names.map((n) => `'${n.replace(/'/g, "''")}'`).join(',');
	return `${personAlias}.person_name IN (${inList})`;
}

/** Build a link URL to a target view, carrying the current context. */
export function contextLink(base: string, path: string, ctx: AnalysisContext, extra?: Record<string, string>): string {
	const params = contextToParams(ctx);
	const extraStr = extra ? '&' + new URLSearchParams(extra).toString() : '';
	return `${base}${path}?${params}${extraStr}`;
}
