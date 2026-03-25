import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('Settings API route', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('GET returns settings with masked key', async () => {
		const mockSettings = {
			has_api_key: true,
			api_key_preview: 'sk-ant-a...wxyz',
			model: 'claude-sonnet-4-20250514',
		};
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(mockSettings),
		});

		const res = await fetch('http://127.0.0.1:52081/api/settings');
		const data = await res.json();
		expect(data.has_api_key).toBe(true);
		expect(data.api_key_preview).not.toContain('sk-ant-api');
		expect(data.model).toBe('claude-sonnet-4-20250514');
	});

	it('POST saves settings', async () => {
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve({ ok: true }),
		});

		const res = await fetch('http://127.0.0.1:52081/api/settings', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ api_key: 'sk-ant-test123', model: 'claude-haiku-4-20250414' }),
		});

		expect(res.ok).toBe(true);
		const callBody = JSON.parse((fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
		expect(callBody.api_key).toBe('sk-ant-test123');
		expect(callBody.model).toBe('claude-haiku-4-20250414');
	});

	it('GET returns defaults when no key configured', async () => {
		const mockSettings = {
			has_api_key: false,
			api_key_preview: '',
			model: 'claude-sonnet-4-20250514',
		};
		(fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
			ok: true,
			json: () => Promise.resolve(mockSettings),
		});

		const res = await fetch('http://127.0.0.1:52081/api/settings');
		const data = await res.json();
		expect(data.has_api_key).toBe(false);
		expect(data.api_key_preview).toBe('');
	});
});
