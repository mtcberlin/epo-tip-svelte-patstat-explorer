import { describe, it, expect } from 'vitest';

/**
 * Tests for the MCP-powered agentic loop.
 * These test the data transformation and protocol handling.
 */

describe('MCP tool format → Anthropic tool format', () => {
	interface McpTool {
		name: string;
		description: string;
		inputSchema: Record<string, unknown>;
	}

	function convertMcpToolsToAnthropic(mcpTools: McpTool[]) {
		return mcpTools.map((t) => ({
			name: t.name,
			description: t.description,
			input_schema: t.inputSchema,
		}));
	}

	it('converts MCP tool list to Anthropic format', () => {
		const mcpTools: McpTool[] = [
			{
				name: 'list_tables',
				description: 'List all available tables',
				inputSchema: { type: 'object', properties: {}, required: [] },
			},
			{
				name: 'execute_query',
				description: 'Execute a SQL query',
				inputSchema: {
					type: 'object',
					properties: {
						query: { type: 'string', description: 'SQL query' },
						max_results: { type: 'integer', default: 1000 },
					},
					required: ['query'],
				},
			},
		];

		const result = convertMcpToolsToAnthropic(mcpTools);

		expect(result).toHaveLength(2);
		expect(result[0].name).toBe('list_tables');
		expect(result[0].input_schema).toEqual(mcpTools[0].inputSchema);
		expect(result[1].name).toBe('execute_query');
		// Anthropic uses input_schema, MCP uses inputSchema
		expect(result[1]).not.toHaveProperty('inputSchema');
		expect(result[1]).toHaveProperty('input_schema');
	});
});

describe('SSE event parsing', () => {
	function parseSSELine(line: string): { event: string; data: string } | null {
		if (!line.startsWith('data: ')) return null;
		const raw = line.slice(6);
		try {
			return JSON.parse(raw);
		} catch {
			return null;
		}
	}

	it('parses a step event', () => {
		const line = 'data: {"event":"step","data":{"type":"tool_call","name":"list_tables","input":{}}}';
		const parsed = parseSSELine(line);
		expect(parsed).toEqual({
			event: 'step',
			data: { type: 'tool_call', name: 'list_tables', input: {} },
		});
	});

	it('parses a sql event', () => {
		const line = 'data: {"event":"sql","data":{"sql":"SELECT 1"}}';
		const parsed = parseSSELine(line);
		expect(parsed?.event).toBe('sql');
		expect(parsed?.data).toEqual({ sql: 'SELECT 1' });
	});

	it('parses an error event', () => {
		const line = 'data: {"event":"error","data":{"message":"Max iterations reached"}}';
		const parsed = parseSSELine(line);
		expect(parsed?.event).toBe('error');
	});

	it('returns null for non-data lines', () => {
		expect(parseSSELine('')).toBeNull();
		expect(parseSSELine('event: step')).toBeNull();
		expect(parseSSELine(': comment')).toBeNull();
	});
});
