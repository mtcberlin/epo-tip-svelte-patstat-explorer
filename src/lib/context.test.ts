import { describe, it, expect } from 'vitest';
import { parseContext, contextToParams, nameWhereClause, contextLink } from './context';

describe('parseContext', () => {
	it('parses a single name from "name" param', () => {
		const params = new URLSearchParams('name=SIEMENS%20AG');
		const ctx = parseContext(params);
		expect(ctx.names).toEqual(['SIEMENS AG']);
		expect(ctx.label).toBe('SIEMENS AG');
	});

	it('parses multiple names from "names" param with ||| separator', () => {
		const params = new URLSearchParams('names=SIEMENS%20AG|||SIEMENS%20LTD&label=Siemens');
		const ctx = parseContext(params);
		expect(ctx.names).toEqual(['SIEMENS AG', 'SIEMENS LTD']);
		expect(ctx.label).toBe('Siemens');
	});

	it('returns empty names for missing params', () => {
		const ctx = parseContext(new URLSearchParams());
		expect(ctx.names).toEqual([]);
		expect(ctx.label).toBe('');
	});

	it('parses optional cpc, from, to', () => {
		const params = new URLSearchParams('name=X&cpc=H01M&from=2015&to=2024');
		const ctx = parseContext(params);
		expect(ctx.cpc).toBe('H01M');
		expect(ctx.from).toBe(2015);
		expect(ctx.to).toBe(2024);
	});

	it('leaves cpc/from/to undefined when not set', () => {
		const ctx = parseContext(new URLSearchParams('name=X'));
		expect(ctx.cpc).toBeUndefined();
		expect(ctx.from).toBeUndefined();
		expect(ctx.to).toBeUndefined();
	});

	it('prefers "names" over "name" when both present', () => {
		const params = new URLSearchParams('name=A&names=B|||C');
		const ctx = parseContext(params);
		// URLSearchParams.get('names') is checked first if present
		expect(ctx.names).toEqual(['B', 'C']);
	});
});

describe('contextToParams', () => {
	it('encodes single name as "name"', () => {
		const str = contextToParams({ names: ['BASF SE'], label: 'BASF SE' });
		const p = new URLSearchParams(str);
		expect(p.get('name')).toBe('BASF SE');
		expect(p.has('names')).toBe(false);
		expect(p.has('label')).toBe(false); // label matches name[0], omitted
	});

	it('encodes multiple names as "names" with ||| separator', () => {
		const str = contextToParams({ names: ['A', 'B'], label: 'Group' });
		const p = new URLSearchParams(str);
		expect(p.get('names')).toBe('A|||B');
		expect(p.get('label')).toBe('Group');
	});

	it('encodes empty context as empty string', () => {
		const str = contextToParams({ names: [], label: '' });
		expect(str).toBe('');
	});

	it('includes optional fields when present', () => {
		const str = contextToParams({ names: ['X'], label: 'X', cpc: 'H01M', from: 2015, to: 2024 });
		const p = new URLSearchParams(str);
		expect(p.get('cpc')).toBe('H01M');
		expect(p.get('from')).toBe('2015');
		expect(p.get('to')).toBe('2024');
	});
});

describe('nameWhereClause', () => {
	it('returns 1=0 for empty names', () => {
		expect(nameWhereClause({ names: [], label: '' })).toBe('1=0');
	});

	it('generates equality clause for single name', () => {
		const clause = nameWhereClause({ names: ['BASF SE'], label: '' });
		expect(clause).toBe("p.person_name = 'BASF SE'");
	});

	it('generates IN clause for multiple names', () => {
		const clause = nameWhereClause({ names: ['A', 'B', 'C'], label: '' });
		expect(clause).toBe("p.person_name IN ('A','B','C')");
	});

	it('escapes single quotes in names', () => {
		const clause = nameWhereClause({ names: ["O'NEAL CORP"], label: '' });
		expect(clause).toBe("p.person_name = 'O''NEAL CORP'");
	});

	it('uses custom person alias', () => {
		const clause = nameWhereClause({ names: ['X'], label: '' }, 'p_ctx');
		expect(clause).toBe("p_ctx.person_name = 'X'");
	});

	it('escapes quotes in IN clause', () => {
		const clause = nameWhereClause({ names: ["A'B", "C'D"], label: '' });
		expect(clause).toBe("p.person_name IN ('A''B','C''D')");
	});
});

describe('contextLink', () => {
	it('builds a link with context params', () => {
		const link = contextLink('', '/applicant', { names: ['X'], label: 'X' });
		expect(link).toBe('/applicant?name=X');
	});

	it('includes extra params', () => {
		const link = contextLink('', '/network', { names: ['X'], label: 'X' }, { view: 'graph' });
		expect(link).toContain('name=X');
		expect(link).toContain('view=graph');
	});

	it('uses base path', () => {
		const link = contextLink('/proxy/52080', '/search', { names: [], label: '' });
		expect(link).toBe('/proxy/52080/search?');
	});
});
