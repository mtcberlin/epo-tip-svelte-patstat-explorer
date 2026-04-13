<script lang="ts">
	import { base } from '$app/paths';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Input } from '$lib/components/ui/input';
	import { downloadCsv } from '$lib/csv';
	import PatentDetailSheet from '$lib/components/patent-detail-sheet.svelte';
	import Settings from '@lucide/svelte/icons/settings';
	import Play from '@lucide/svelte/icons/play';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import DatabaseZap from '@lucide/svelte/icons/database-zap';
	import Send from '@lucide/svelte/icons/send';

	// --- State ---
	let mode = $state<string>('nl');
	let nlInput = $state('');
	let sqlInput = $state('');
	let generatedSql = $state('');
	let results = $state<Record<string, unknown>[]>([]);
	let columns = $state<string[]>([]);
	let loading = $state(false);
	let generating = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);

	// Chat history for NL mode
	interface AgentStep {
		event: string;
		data: Record<string, unknown>;
	}
	interface ChatMessage {
		role: 'user' | 'assistant';
		content: string;
		sql?: string;
		steps?: AgentStep[];
	}
	let chatHistory = $state<ChatMessage[]>([]);
	let agentSteps = $state<AgentStep[]>([]);

	// Settings dialog
	let settingsOpen = $state(false);
	let apiKey = $state('');
	let selectedModel = $state('claude-sonnet-4-20250514');
	let hasApiKey = $state(false);
	let apiKeyPreview = $state('');
	let settingsLoading = $state(false);
	let settingsError = $state('');

	const models = [
		{ value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
		{ value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
	];

	// --- API helpers ---
	async function runQuery(sql: string): Promise<Record<string, unknown>[]> {
		const res = await fetch(`${base}/api/query`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ sql })
		});
		if (!res.ok) {
			const text = await res.text();
			throw new Error(text);
		}
		const data = await res.json();
		return data.rows ?? data;
	}

	async function nlToSqlStream(question: string, history: { role: string; content: string }[]): Promise<{ text: string; steps: AgentStep[] }> {
		const res = await fetch(`${base}/api/nl-to-sql`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ question, history })
		});
		if (!res.ok) {
			const text = await res.text();
			let detail = text;
			try { detail = JSON.parse(text).message ?? text; } catch {}
			throw new Error(detail);
		}

		const reader = res.body?.getReader();
		if (!reader) throw new Error('No response stream');

		const decoder = new TextDecoder();
		let buffer = '';
		let resultText = '';
		const steps: AgentStep[] = [];

		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			const lines = buffer.split('\n');
			buffer = lines.pop() ?? '';

			for (const line of lines) {
				if (!line.startsWith('data: ')) continue;
				let event: AgentStep;
				try {
					event = JSON.parse(line.slice(6)) as AgentStep;
				} catch {
					// Malformed SSE line — skip it, but don't mask real backend errors.
					continue;
				}
				if (event.event === 'done') continue;

				steps.push(event);
				agentSteps = [...steps];

				if (event.event === 'result') {
					resultText = String(event.data.text ?? '');
				} else if (event.event === 'error') {
					throw new Error(String(event.data.message ?? 'Agent error'));
				}
			}
		}

		return { text: resultText, steps };
	}

	// --- Settings ---
	async function loadSettings() {
		try {
			const res = await fetch(`${base}/api/settings`);
			if (res.ok) {
				const data = await res.json();
				hasApiKey = data.has_api_key;
				apiKeyPreview = data.api_key_preview ?? '';
				selectedModel = data.model ?? 'claude-sonnet-4-20250514';
			}
		} catch {}
	}

	async function saveSettings() {
		settingsLoading = true;
		settingsError = '';
		try {
			const body: Record<string, string> = { model: selectedModel };
			if (apiKey) body.api_key = apiKey;
			const res = await fetch(`${base}/api/settings`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			if (!res.ok) throw new Error('Failed to save');
			apiKey = '';
			await loadSettings();
			settingsOpen = false;
		} catch (e) {
			settingsError = e instanceof Error ? e.message : String(e);
		} finally {
			settingsLoading = false;
		}
	}

	$effect(() => {
		loadSettings();
	});

	// --- NL mode: ask question ---
	async function askQuestion() {
		const q = nlInput.trim();
		if (!q) return;

		generating = true;
		errorMsg = '';
		nlInput = '';
		agentSteps = [];

		chatHistory = [...chatHistory, { role: 'user', content: q }];

		// Build history for API (pairs of user/assistant messages)
		const apiHistory = chatHistory.slice(0, -1).map((m) => ({
			role: m.role,
			content: m.role === 'assistant' ? (m.sql ?? m.content) : m.content
		}));

		try {
			const { text, steps } = await nlToSqlStream(q, apiHistory);
			if (!text.trim()) {
				throw new Error('The agent finished without producing any SQL. Try rephrasing your question.');
			}
			generatedSql = text;
			chatHistory = [...chatHistory, { role: 'assistant', content: 'Generated SQL query.', sql: text, steps }];
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
			chatHistory = chatHistory.slice(0, -1);
		} finally {
			generating = false;
			agentSteps = [];
		}
	}

	// --- Execute SQL (from either mode) ---
	async function executeSql(sql?: string) {
		const query = sql ?? (mode === 'sql' ? sqlInput.trim() : generatedSql.trim());
		if (!query) return;

		loading = true;
		errorMsg = '';
		results = [];
		columns = [];
		const t0 = performance.now();

		try {
			const rows = await runQuery(query);
			results = rows;
			columns = rows.length > 0 ? Object.keys(rows[0]) : [];
			elapsed = Math.round(performance.now() - t0);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	// --- Key handlers ---
	function handleNlKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			askQuestion();
		}
	}

	function handleSqlKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
			e.preventDefault();
			executeSql();
		}
	}

	// Sort state
	let detailOpen = $state(false);
	let detailApplnId = $state<number | null>(null);

	let sortCol = $state('');
	let sortAsc = $state(true);

	function sortBy(col: string) {
		if (sortCol === col) {
			sortAsc = !sortAsc;
		} else {
			sortCol = col;
			sortAsc = true;
		}
	}

	const sortedResults = $derived(() => {
		if (!sortCol) return results;
		return [...results].sort((a, b) => {
			const va = a[sortCol];
			const vb = b[sortCol];
			if (va == null && vb == null) return 0;
			if (va == null) return sortAsc ? -1 : 1;
			if (vb == null) return sortAsc ? 1 : -1;
			if (typeof va === 'number' && typeof vb === 'number') {
				return sortAsc ? va - vb : vb - va;
			}
			const sa = String(va);
			const sb = String(vb);
			return sortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
		});
	});
</script>

<svelte:head>
	<title>AI Query | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header with settings button -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold">AI Query Interface</h1>
			<p class="text-sm text-muted-foreground mt-1">
				Ask questions in natural language or write SQL directly.
			</p>
		</div>
		<Button variant="outline" size="sm" onclick={() => (settingsOpen = true)}>
			<Settings class="size-4" />
			Settings
		</Button>
	</div>

	<!-- Mode tabs -->
	<Tabs.Root bind:value={mode}>
		<Tabs.List>
			<Tabs.Trigger value="nl">
				<Sparkles class="size-4 mr-1.5" />
				Natural Language
			</Tabs.Trigger>
			<Tabs.Trigger value="sql">
				<DatabaseZap class="size-4 mr-1.5" />
				SQL
			</Tabs.Trigger>
		</Tabs.List>

		<!-- NL Mode -->
		<Tabs.Content value="nl">
			<Card.Root>
				<Card.Content class="space-y-4 pt-4">
					<!-- Chat history -->
					{#if chatHistory.length > 0 || generating}
						<div class="space-y-3 max-h-80 overflow-y-auto">
							{#each chatHistory as msg}
								{#if msg.role === 'user'}
									<div class="flex gap-3">
										<div class="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-[var(--mtc-blue)] text-white">
											{msg.content}
										</div>
									</div>
								{:else}
									<div class="w-full rounded-lg px-4 py-3 text-sm bg-muted text-foreground space-y-3">
										<div>{msg.content}</div>
										{#if msg.sql}
											<pre class="rounded-lg bg-background border p-3 text-xs overflow-x-auto font-mono leading-relaxed whitespace-pre-wrap">{msg.sql}</pre>
											<div class="flex items-center gap-2">
												<Button size="sm" onclick={() => executeSql(msg.sql)} disabled={loading}>
													<Play class="size-3.5" />
													{loading ? 'Running...' : 'Run'}
												</Button>
												<Button size="sm" variant="ghost" onclick={() => { sqlInput = msg.sql ?? ''; mode = 'sql'; }}>
													Edit in SQL tab
												</Button>
											</div>
										{/if}
										{#if msg.steps && msg.steps.length > 0}
											{@const mcpInfo = msg.steps.find(s => s.event === 'mcp_connected')}
											<div class="space-y-1.5 text-xs opacity-75">
												{#if mcpInfo}
													<div class="flex items-center gap-2 mb-1">
														<span class="inline-flex items-center rounded-md bg-[var(--mtc-navy)] text-white px-1.5 py-0.5 font-medium">MCP</span>
														<span>{mcpInfo.data.server}</span>
													</div>
												{/if}
												{#each msg.steps.filter(s => s.event === 'tool_call') as step}
													<div class="flex items-center gap-1.5">
														<span class="font-mono bg-black/10 rounded px-1">{step.data.name}</span>
														{#if step.data.input && Object.keys(step.data.input).length > 0}
															<span class="break-all">{JSON.stringify(step.data.input)}</span>
														{/if}
													</div>
												{/each}
											</div>
										{/if}
									</div>
								{/if}
							{/each}
							{#if generating}
								<div class="flex gap-3 flex-row-reverse">
									<div class="w-full bg-muted rounded-lg px-4 py-3 text-sm space-y-2.5">
										{#if agentSteps.length > 0}
											{@const mcpStep = agentSteps.find(s => s.event === 'mcp_connected')}
											{#if mcpStep}
												<div class="flex items-center gap-2 text-xs">
													<span class="inline-flex items-center gap-1 rounded-md bg-[var(--mtc-navy)] text-white px-1.5 py-0.5 font-medium">
														MCP
													</span>
													<span class="text-muted-foreground">{mcpStep.data.server}</span>
													<span class="text-muted-foreground/60">&middot; {mcpStep.data.tool_count} tools</span>
												</div>
											{/if}
											<div class="space-y-1.5 text-xs">
												{#each agentSteps as step}
													{#if step.event === 'tool_call'}
														<div class="flex items-center gap-1.5 text-[var(--mtc-blue)]">
															<span class="animate-pulse">●</span>
															<span class="inline-flex items-center rounded bg-[var(--mtc-navy)]/10 px-1 py-0.5 font-mono text-[var(--mtc-navy)]">MCP</span>
															<span class="font-mono">{step.data.name}</span>
															{#if step.data.input && Object.keys(step.data.input).length > 0}
																<span class="text-muted-foreground break-all">{JSON.stringify(step.data.input)}</span>
															{/if}
														</div>
													{:else if step.event === 'tool_result'}
														<div class="text-muted-foreground pl-3 break-words">
															✓ {String(step.data.result ?? '').slice(0, 120)}
														</div>
													{/if}
												{/each}
											</div>
										{:else}
											<div class="flex items-center gap-2 text-muted-foreground">
												<span class="animate-pulse">●</span>
												Querying PATSTAT via MCP...
											</div>
										{/if}
									</div>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Input -->
					<form onsubmit={(e) => { e.preventDefault(); askQuestion(); }} class="flex gap-2">
						<Textarea
							bind:value={nlInput}
							onkeydown={handleNlKeydown}
							placeholder="e.g. Find all PEM electrolysis patents from European applicants since 2018 with at least 5 citations"
							class="min-h-10 max-h-32 resize-none"
							rows={1}
							disabled={generating}
						/>
						<Button type="submit" disabled={generating || !nlInput.trim() || !hasApiKey} size="icon">
							<Send class="size-4" />
						</Button>
					</form>

					{#if !hasApiKey}
						<p class="text-xs text-muted-foreground">
							No API key configured.
							<button class="underline text-[var(--mtc-blue)]" onclick={() => (settingsOpen = true)}>
								Add your Anthropic API key
							</button> to use Natural Language mode.
						</p>
					{/if}
				</Card.Content>
			</Card.Root>
		</Tabs.Content>

		<!-- SQL Mode -->
		<Tabs.Content value="sql">
			<Card.Root>
				<Card.Content class="space-y-3 pt-4">
					<Textarea
						bind:value={sqlInput}
						onkeydown={handleSqlKeydown}
						placeholder="SELECT p.person_name, COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls206_person p
JOIN tls207_pers_appln pa ON p.person_id = pa.person_id
JOIN tls201_appln a ON pa.appln_id = a.appln_id
WHERE pa.applt_seq_nr > 0
GROUP BY p.person_name
ORDER BY families DESC
LIMIT 20"
						class="min-h-40 font-mono text-xs"
						rows={8}
					/>
					<div class="flex items-center gap-2">
						<Button onclick={() => executeSql()} disabled={loading || !sqlInput.trim()}>
							<Play class="size-3.5" />
							{loading ? 'Running...' : 'Run Query'}
						</Button>
						<span class="text-xs text-muted-foreground">Ctrl+Enter to run</span>
					</div>
				</Card.Content>
			</Card.Root>
		</Tabs.Content>
	</Tabs.Root>

	<!-- Error -->
	{#if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">
			{errorMsg}
		</div>
	{/if}

	<!-- Results -->
	{#if results.length > 0}
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<div>
					<Card.Title>{results.length} rows returned</Card.Title>
					<Card.Description>{elapsed}ms{columns.includes('appln_id') ? ' · Click a row for patent details' : ''}</Card.Description>
				</div>
				<Button variant="outline" size="sm" onclick={() => downloadCsv(results, 'query_results.csv')}>
					Export CSV
				</Button>
			</Card.Header>
			<Card.Content class="p-0">
				<div class="overflow-x-auto max-h-[500px] overflow-y-auto">
					<Table.Root>
						<Table.Header>
							<Table.Row>
								{#each columns as col}
									<Table.Head>
										<button
											class="flex items-center gap-1 hover:text-foreground transition-colors"
											onclick={() => sortBy(col)}
										>
											{col}
											{#if sortCol === col}
												<span class="text-xs">{sortAsc ? '↑' : '↓'}</span>
											{/if}
										</button>
									</Table.Head>
								{/each}
							</Table.Row>
						</Table.Header>
						<Table.Body>
							{#each sortedResults() as row}
								<Table.Row
									class={row['appln_id'] != null ? 'cursor-pointer hover:bg-muted/50' : ''}
									onclick={() => {
										if (row['appln_id'] != null) {
											detailApplnId = Number(row['appln_id']);
											detailOpen = true;
										}
									}}
								>
									{#each columns as col}
										<Table.Cell class="text-xs max-w-xs truncate" title={String(row[col] ?? '')}>
											{row[col] ?? ''}
										</Table.Cell>
									{/each}
								</Table.Row>
							{/each}
						</Table.Body>
					</Table.Root>
				</div>
			</Card.Content>
		</Card.Root>
	{:else if !loading && !errorMsg && (generatedSql || sqlInput)}
		<!-- Show nothing until query is run -->
	{/if}

	<!-- Examples -->
	{#if chatHistory.length === 0 && mode === 'nl' && !results.length}
		<Card.Root>
			<Card.Header>
				<Card.Title class="text-base">Example Questions</Card.Title>
			</Card.Header>
			<Card.Content>
				<div class="grid gap-2 sm:grid-cols-2">
					{#each [
						'Top 10 applicants in solid-state battery patents (CPC H01M10) since 2015',
						'Patent families filed by BASF in the last 5 years, grouped by CPC section',
						'Countries with the most patent filings in mRNA technology (2020-2024)',
						'Most cited patent families in autonomous driving (CPC B60W)',
						'Co-applicants of SIEMENS AG with more than 10 shared patent families',
						'Number of patent families per year for hydrogen fuel cells (H01M8)'
					] as example}
						<button
							class="rounded-lg border p-3 text-left text-sm text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
							onclick={() => { nlInput = example; }}
						>
							{example}
						</button>
					{/each}
				</div>
			</Card.Content>
		</Card.Root>
	{/if}
</div>

<!-- Settings Dialog -->
<Dialog.Root bind:open={settingsOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>AI Settings</Dialog.Title>
			<Dialog.Description>
				Configure your Anthropic API key for natural language queries. Your key is stored locally on the server.
			</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-4">
			<div class="space-y-2">
				<label for="api-key" class="text-sm font-medium">Anthropic API Key</label>
				{#if hasApiKey}
					<p class="text-xs text-muted-foreground">
						Current key: <code class="bg-muted px-1 rounded">{apiKeyPreview}</code>
					</p>
				{/if}
				<Input
					id="api-key"
					type="password"
					bind:value={apiKey}
					placeholder={hasApiKey ? 'Enter new key to replace...' : 'sk-ant-...'}
				/>
			</div>
			<div class="space-y-2">
				<label for="model-select" class="text-sm font-medium">Model</label>
				<select
					id="model-select"
					bind:value={selectedModel}
					class="flex h-8 w-full rounded-lg border border-input bg-background px-2.5 py-1 text-sm"
				>
					{#each models as m}
						<option value={m.value}>{m.label}</option>
					{/each}
				</select>
			</div>
			{#if settingsError}
				<p class="text-sm text-destructive">{settingsError}</p>
			{/if}
		</div>
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (settingsOpen = false)}>Cancel</Button>
			<Button onclick={saveSettings} disabled={settingsLoading}>
				{settingsLoading ? 'Saving...' : 'Save'}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<PatentDetailSheet bind:open={detailOpen} bind:applnId={detailApplnId} />
