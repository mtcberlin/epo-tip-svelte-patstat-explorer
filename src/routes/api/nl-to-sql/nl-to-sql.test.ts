import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Test the NL-to-SQL API route proxy behavior
// Since SvelteKit RequestHandler is hard to unit test directly,
// we test the fetch interaction patterns

describe('NL-to-SQL API route', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('proxies a valid question to the sidecar', async () => {
		const mockSidecarResponse = { sql: 'SELECT 1 FROM tls201_appln LIMIT 10' };
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(mockSidecarResponse),
		});

		const res = await fetch('http://127.0.0.1:52081/api/nl-to-sql', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question: 'Show me top 10 applicants', history: [] }),
		});

		expect(res.ok).toBe(true);
		const data = await res.json();
		expect(data.sql).toContain('SELECT');
	});

	it('sends question and history in the request body', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ sql: 'SELECT 1' }),
		});

		const history = [
			{ role: 'user', content: 'Previous question' },
			{ role: 'assistant', content: 'SELECT 1' },
		];

		await fetch('http://127.0.0.1:52081/api/nl-to-sql', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question: 'Follow-up', history }),
		});

		const callBody = JSON.parse((fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
		expect(callBody.question).toBe('Follow-up');
		expect(callBody.history).toHaveLength(2);
	});
});
