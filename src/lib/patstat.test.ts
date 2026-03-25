import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { queryPatstat, healthCheck } from './patstat';

describe('queryPatstat', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('sends POST with SQL to sidecar', async () => {
		const mockResponse = [{ name: 'BASF', count: 10 }];
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(mockResponse),
		});

		const result = await queryPatstat('SELECT 1');
		expect(fetch).toHaveBeenCalledWith(
			'http://127.0.0.1:52081/api/query',
			expect.objectContaining({
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ sql: 'SELECT 1' }),
			})
		);
		expect(result).toEqual(mockResponse);
	});

	it('throws on non-ok response', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: false,
			status: 400,
			text: () => Promise.resolve('Bad query'),
		});

		await expect(queryPatstat('INVALID')).rejects.toThrow('PATSTAT query failed (400): Bad query');
	});
});

describe('healthCheck', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('returns ok status on success', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ ok: true, message: 'connected' }),
		});

		const result = await healthCheck();
		expect(result).toEqual({ ok: true, message: 'connected' });
	});

	it('returns error on non-ok response', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: false,
			status: 503,
		});

		const result = await healthCheck();
		expect(result.ok).toBe(false);
		expect(result.message).toContain('Status 503');
	});

	it('returns error on network failure', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('ECONNREFUSED'));

		const result = await healthCheck();
		expect(result.ok).toBe(false);
		expect(result.message).toContain('ECONNREFUSED');
	});
});
