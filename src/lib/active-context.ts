/**
 * Persistent active analysis context.
 *
 * Survives navigation between pages (stored in localStorage).
 * The context bar in the layout reads from this, and pages
 * that load applicant context write to it.
 */

import type { AnalysisContext } from './context';

const STORAGE_KEY = 'patstat-active-context';

interface StoredContext {
	names: string[];
	label: string;
	cpc?: string;
	from?: number;
	to?: number;
}

function _read(): StoredContext | null {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw) as StoredContext;
		if (!parsed.names || parsed.names.length === 0) return null;
		return parsed;
	} catch {
		return null;
	}
}

function _write(ctx: StoredContext | null): void {
	try {
		if (ctx) {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(ctx));
		} else {
			localStorage.removeItem(STORAGE_KEY);
		}
	} catch {
		// localStorage unavailable (SSR, private mode) — silently ignore
	}
}

export function getActiveContext(): AnalysisContext | null {
	return _read();
}

export function setActiveContext(ctx: AnalysisContext): void {
	if (!ctx.names || ctx.names.length === 0) {
		_write(null);
		return;
	}
	_write({
		names: ctx.names,
		label: ctx.label,
		cpc: ctx.cpc,
		from: ctx.from,
		to: ctx.to,
	});
}

export function clearActiveContext(): void {
	_write(null);
}
