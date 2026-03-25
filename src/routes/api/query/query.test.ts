import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// We test the validateSql logic directly since the RequestHandler
// depends on SvelteKit internals. Extract the validation for testability.

// For now, replicate the validation logic to test it in isolation.
// TODO: Extract validateSql to a shared module for direct import.

const MAX_SQL_LENGTH = 10_000;

function validateSql(sql: string): string | null {
	const trimmed = sql.trim();
	if (trimmed.length > MAX_SQL_LENGTH) return 'Query too long';
	if (!/^SELECT\b/i.test(trimmed)) return 'Only SELECT queries are allowed';
	if (/;\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|REVOKE)\b/i.test(trimmed)) return 'Multiple statements not allowed';
	return null;
}

describe('SQL validation', () => {
	it('allows valid SELECT queries', () => {
		expect(validateSql('SELECT 1')).toBeNull();
		expect(validateSql('SELECT * FROM tls201_appln LIMIT 10')).toBeNull();
		expect(validateSql('  SELECT p.person_name FROM tls206_person p  ')).toBeNull();
	});

	it('allows case-insensitive SELECT', () => {
		expect(validateSql('select 1')).toBeNull();
		expect(validateSql('Select * from foo')).toBeNull();
	});

	it('rejects non-SELECT queries', () => {
		expect(validateSql('INSERT INTO foo VALUES (1)')).toBe('Only SELECT queries are allowed');
		expect(validateSql('DELETE FROM foo')).toBe('Only SELECT queries are allowed');
		expect(validateSql('DROP TABLE foo')).toBe('Only SELECT queries are allowed');
		expect(validateSql('UPDATE foo SET x=1')).toBe('Only SELECT queries are allowed');
		expect(validateSql('ALTER TABLE foo ADD col INT')).toBe('Only SELECT queries are allowed');
	});

	it('rejects multiple statements', () => {
		expect(validateSql('SELECT 1; DROP TABLE foo')).toBe('Multiple statements not allowed');
		expect(validateSql('SELECT 1; SELECT 2')).toBe('Multiple statements not allowed');
		expect(validateSql('SELECT 1;INSERT INTO foo VALUES(1)')).toBe('Multiple statements not allowed');
	});

	it('allows semicolons in string literals (no keyword after)', () => {
		// Semicolons not followed by SQL keywords are ok
		expect(validateSql("SELECT * FROM foo WHERE name LIKE 'a;b'")).toBeNull();
	});

	it('rejects queries exceeding max length', () => {
		const longQuery = 'SELECT ' + 'x'.repeat(MAX_SQL_LENGTH);
		expect(validateSql(longQuery)).toBe('Query too long');
	});

	it('handles empty and whitespace-only input', () => {
		expect(validateSql('')).toBe('Only SELECT queries are allowed');
		expect(validateSql('   ')).toBe('Only SELECT queries are allowed');
	});
});
