import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Co-occurrence API route', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('sends where_clause to sidecar and returns matrix data', async () => {
		const mockMatrix = [
			{ section1: 'A', section2: 'B', family_count: 42 },
			{ section1: 'A', section2: 'C', family_count: 10 },
		];
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(mockMatrix),
		});

		const res = await fetch('http://127.0.0.1:52081/api/co-occurrence', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ where_clause: "p.person_name = 'BASF SE'" }),
		});

		expect(res.ok).toBe(true);
		const data = await res.json();
		expect(data).toHaveLength(2);
		expect(data[0].section1).toBe('A');
		expect(data[0].family_count).toBe(42);
	});
});

describe('Co-occurrence matrix transformation', () => {
	const CPC_SECTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'Y'];

	function buildMatrix(
		data: { section1: string; section2: string; family_count: number }[]
	): { row: string; col: string; count: number }[] {
		const lookup = new Map<string, number>();
		for (const d of data) {
			lookup.set(`${d.section1}-${d.section2}`, d.family_count);
			lookup.set(`${d.section2}-${d.section1}`, d.family_count); // symmetric
		}

		const cells: { row: string; col: string; count: number }[] = [];
		for (const row of CPC_SECTIONS) {
			for (const col of CPC_SECTIONS) {
				cells.push({
					row,
					col,
					count: lookup.get(`${row}-${col}`) ?? 0,
				});
			}
		}
		return cells;
	}

	it('builds a symmetric 9x9 matrix from sparse data', () => {
		const data = [
			{ section1: 'A', section2: 'B', family_count: 42 },
			{ section1: 'H', section2: 'Y', family_count: 7 },
		];
		const matrix = buildMatrix(data);
		expect(matrix).toHaveLength(81); // 9x9

		// Check A-B and B-A are both 42 (symmetric)
		const ab = matrix.find((c) => c.row === 'A' && c.col === 'B');
		const ba = matrix.find((c) => c.row === 'B' && c.col === 'A');
		expect(ab?.count).toBe(42);
		expect(ba?.count).toBe(42);

		// Check H-Y
		const hy = matrix.find((c) => c.row === 'H' && c.col === 'Y');
		expect(hy?.count).toBe(7);

		// Check empty cell
		const cd = matrix.find((c) => c.row === 'C' && c.col === 'D');
		expect(cd?.count).toBe(0);
	});

	it('handles empty data', () => {
		const matrix = buildMatrix([]);
		expect(matrix).toHaveLength(81);
		expect(matrix.every((c) => c.count === 0)).toBe(true);
	});

	it('finds max count for color scaling', () => {
		const data = [
			{ section1: 'A', section2: 'A', family_count: 100 },
			{ section1: 'A', section2: 'B', family_count: 50 },
		];
		const matrix = buildMatrix(data);
		const maxCount = Math.max(...matrix.map((c) => c.count));
		expect(maxCount).toBe(100);
	});
});
