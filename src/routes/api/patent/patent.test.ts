import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Patent Detail API route', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('proxies appln_id to sidecar and returns patent details', async () => {
		const mockPatent = {
			appln_id: 42,
			appln_auth: 'EP',
			appln_nr: '1234567',
			appln_kind: 'A',
			appln_filing_date: '2020-03-15',
			appln_filing_year: 2020,
			docdb_family_id: 99999,
			granted: 1,
			title: 'Method for energy storage',
			title_lang: 'en',
			abstract: 'A method for improved energy storage.',
			applicants: [
				{ person_name: 'SIEMENS AG', person_ctry_code: 'DE' },
			],
			cpc_codes: ['H01M10/0562'],
		};
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(mockPatent),
		});

		const res = await fetch('http://127.0.0.1:52081/api/patent/42');
		expect(res.ok).toBe(true);
		const data = await res.json();
		expect(data.appln_id).toBe(42);
		expect(data.applicants).toHaveLength(1);
		expect(data.cpc_codes).toContain('H01M10/0562');
	});

	it('returns 404 for non-existent patent', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: false,
			status: 404,
			json: () => Promise.resolve({ detail: 'Patent not found' }),
		});

		const res = await fetch('http://127.0.0.1:52081/api/patent/99999999');
		expect(res.ok).toBe(false);
		expect(res.status).toBe(404);
	});
});
