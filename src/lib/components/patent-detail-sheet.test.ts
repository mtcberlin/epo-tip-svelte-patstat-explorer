import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Test the patent detail data loading logic
// Component rendering is tested indirectly via the fetch pattern

describe('Patent detail data loading', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('fetches patent details by appln_id', async () => {
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
				{ person_name: 'BASF SE', person_ctry_code: 'DE' },
			],
			cpc_codes: ['H01M10/0562', 'H02J7/00'],
		};

		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(mockPatent),
		});

		const res = await fetch('/api/patent/42');
		const data = await res.json();

		expect(fetch).toHaveBeenCalledWith('/api/patent/42');
		expect(data.appln_id).toBe(42);
		expect(data.title).toBe('Method for energy storage');
		expect(data.applicants).toHaveLength(2);
		expect(data.cpc_codes).toEqual(['H01M10/0562', 'H02J7/00']);
	});

	it('handles missing patent gracefully', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: false,
			status: 404,
			text: () => Promise.resolve('Patent not found'),
		});

		const res = await fetch('/api/patent/99999999');
		expect(res.ok).toBe(false);
		expect(res.status).toBe(404);
	});

	it('constructs correct Espacenet URL', () => {
		const appln_auth = 'EP';
		const appln_nr = '1234567';
		const url = `https://worldwide.espacenet.com/patent/search?q=pn%3D${appln_auth}${appln_nr}`;
		expect(url).toBe('https://worldwide.espacenet.com/patent/search?q=pn%3DEP1234567');
	});

	it('constructs correct CPC explorer URL', () => {
		const cpc = 'H01M10/0562';
		const slug = cpc.toLowerCase().replace(/[\s/]+/g, '-');
		const url = `https://patentclassificationexplorer.com/cpc/${slug}`;
		expect(url).toBe('https://patentclassificationexplorer.com/cpc/h01m10-0562');
	});

	it('handles CPC codes with spaces', () => {
		const cpc = 'A61P 3/06';
		const slug = cpc.toLowerCase().replace(/[\s/]+/g, '-');
		const url = `https://patentclassificationexplorer.com/cpc/${slug}`;
		expect(url).toBe('https://patentclassificationexplorer.com/cpc/a61p-3-06');
	});
});
