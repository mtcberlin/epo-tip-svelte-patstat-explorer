import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock localStorage
const localStorageMock = (() => {
	let store: Record<string, string> = {};
	return {
		getItem: (key: string) => store[key] ?? null,
		setItem: (key: string, value: string) => { store[key] = value; },
		removeItem: (key: string) => { delete store[key]; },
		clear: () => { store = {}; },
	};
})();

beforeEach(() => {
	localStorageMock.clear();
	vi.stubGlobal('localStorage', localStorageMock);
});

describe('active context store', () => {
	it('starts empty when no localStorage entry exists', async () => {
		const { getActiveContext } = await import('./active-context');
		const ctx = getActiveContext();
		expect(ctx).toBeNull();
	});

	it('stores and retrieves context', async () => {
		// Re-import to get fresh module
		vi.resetModules();
		const { setActiveContext, getActiveContext } = await import('./active-context');

		setActiveContext({ names: ['BASF SE'], label: 'BASF SE' });
		const ctx = getActiveContext();
		expect(ctx).not.toBeNull();
		expect(ctx!.names).toEqual(['BASF SE']);
		expect(ctx!.label).toBe('BASF SE');
	});

	it('persists to localStorage', async () => {
		vi.resetModules();
		const { setActiveContext } = await import('./active-context');

		setActiveContext({ names: ['A', 'B'], label: 'Group' });
		const stored = localStorageMock.getItem('patstat-active-context');
		expect(stored).not.toBeNull();
		const parsed = JSON.parse(stored!);
		expect(parsed.names).toEqual(['A', 'B']);
		expect(parsed.label).toBe('Group');
	});

	it('restores from localStorage on load', async () => {
		localStorageMock.setItem('patstat-active-context', JSON.stringify({
			names: ['SIEMENS AG', 'SIEMENS LTD'],
			label: 'Siemens',
		}));

		vi.resetModules();
		const { getActiveContext } = await import('./active-context');
		const ctx = getActiveContext();
		expect(ctx!.names).toEqual(['SIEMENS AG', 'SIEMENS LTD']);
		expect(ctx!.label).toBe('Siemens');
	});

	it('clears context', async () => {
		vi.resetModules();
		const { setActiveContext, clearActiveContext, getActiveContext } = await import('./active-context');

		setActiveContext({ names: ['X'], label: 'X' });
		expect(getActiveContext()).not.toBeNull();

		clearActiveContext();
		expect(getActiveContext()).toBeNull();
		expect(localStorageMock.getItem('patstat-active-context')).toBeNull();
	});

	it('preserves optional cpc/from/to fields', async () => {
		vi.resetModules();
		const { setActiveContext, getActiveContext } = await import('./active-context');

		setActiveContext({ names: ['X'], label: 'X', cpc: 'H01M', from: 2015, to: 2024 });
		const ctx = getActiveContext();
		expect(ctx!.cpc).toBe('H01M');
		expect(ctx!.from).toBe(2015);
		expect(ctx!.to).toBe(2024);
	});

	it('does not store empty names', async () => {
		vi.resetModules();
		const { setActiveContext, getActiveContext } = await import('./active-context');

		setActiveContext({ names: [], label: '' });
		expect(getActiveContext()).toBeNull();
	});
});
