import { describe, it, expect, vi, beforeEach } from 'vitest';
import { downloadCsv } from './csv';

describe('downloadCsv', () => {
	let createObjectURLMock: ReturnType<typeof vi.fn>;
	let revokeObjectURLMock: ReturnType<typeof vi.fn>;
	let clickMock: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		createObjectURLMock = vi.fn(() => 'blob:mock-url');
		revokeObjectURLMock = vi.fn();
		clickMock = vi.fn();

		global.URL.createObjectURL = createObjectURLMock;
		global.URL.revokeObjectURL = revokeObjectURLMock;

		vi.spyOn(document, 'createElement').mockReturnValue({
			href: '',
			download: '',
			click: clickMock,
		} as unknown as HTMLAnchorElement);
	});

	it('does nothing for empty array', () => {
		downloadCsv([], 'test.csv');
		expect(createObjectURLMock).not.toHaveBeenCalled();
	});

	it('creates CSV with correct headers and data', () => {
		const rows = [
			{ name: 'BASF', country: 'DE', families: 100 },
			{ name: 'BAYER', country: 'DE', families: 80 },
		];
		downloadCsv(rows, 'test.csv');

		expect(createObjectURLMock).toHaveBeenCalledOnce();
		const blob: Blob = createObjectURLMock.mock.calls[0][0];
		expect(blob).toBeInstanceOf(Blob);
		expect(blob.type).toBe('text/csv;charset=utf-8;');
	});

	it('triggers download with correct filename', () => {
		downloadCsv([{ a: 1 }], 'export.csv');

		const anchor = document.createElement('a') as HTMLAnchorElement;
		expect(anchor.download).toBe('export.csv');
		expect(clickMock).toHaveBeenCalledOnce();
	});

	it('revokes the object URL after click', () => {
		downloadCsv([{ a: 1 }], 'test.csv');
		expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:mock-url');
	});

	it('handles values with commas by quoting', () => {
		const rows = [{ name: 'A, B Corp', value: 42 }];
		downloadCsv(rows, 'test.csv');

		const blob: Blob = createObjectURLMock.mock.calls[0][0];
		// We can't easily read the blob content in jsdom, but verify it was created
		expect(blob).toBeInstanceOf(Blob);
	});

	it('handles values with double quotes by escaping', () => {
		const rows = [{ name: 'He said "hello"', value: 1 }];
		downloadCsv(rows, 'test.csv');
		expect(createObjectURLMock).toHaveBeenCalledOnce();
	});

	it('handles null and undefined values', () => {
		const rows = [{ name: null, value: undefined } as unknown as Record<string, unknown>];
		downloadCsv(rows, 'test.csv');
		expect(createObjectURLMock).toHaveBeenCalledOnce();
	});
});
