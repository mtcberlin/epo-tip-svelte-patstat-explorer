<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { BarChart } from 'layerchart';
	import { downloadCsv } from '$lib/csv';
	import { parseContext, nameWhereClause } from '$lib/context';
	import ConsolidatedNames from '$lib/components/consolidated-names.svelte';

	const ctx = $derived(parseContext(page.url.searchParams));
	const hasApplicantFilter = $derived(ctx.names.length > 0);

	let query = $state('');
	let topApplicants = $state<{ name: string; country: string; families: number }[]>([]);
	let trend = $state<{ year: number; families: number }[]>([]);
	let cpcSuggestions = $state<{ symbol: string; title_en: string }[]>([]);
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);

	// CPC code shape: A (section), H01 (class), H01M (subclass), H01M10 (group),
	// H01M10/052 (subgroup). Digits and letters past the section are all optional.
	const CPC_RE = /^[A-Z]([0-9]{1,2}([A-Z]([0-9]{1,4}(\/[0-9]{1,6})?)?)?)?$/;
	function isCpcCode(s: string): boolean {
		return CPC_RE.test(s.trim().toUpperCase());
	}

	async function runQuery(sql: string): Promise<any[]> {
		const res = await fetch(`${base}/api/query`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ sql })
		});
		if (!res.ok) throw new Error(await res.text());
		const data = await res.json();
		return data.rows ?? data;
	}

	function resetResults() {
		topApplicants = [];
		trend = [];
		cpcSuggestions = [];
		errorMsg = '';
	}

	async function handleSubmit() {
		const raw = query.trim();
		if (!raw) return;
		if (isCpcCode(raw)) {
			query = raw.toUpperCase();
			await search();
		} else {
			await searchDescriptions(raw);
		}
	}

	async function searchDescriptions(text: string) {
		loading = true;
		resetResults();
		const t0 = performance.now();

		// Split into words ≥ 3 chars (drops "of", "in", etc. that would dominate hits).
		// Each word is escaped and matched independently. Results are ranked by how many
		// of the user's words appear, so multi-word queries don't fail just because the
		// exact phrase isn't in any CPC title (they almost never are).
		const words = text
			.toLowerCase()
			.split(/\s+/)
			.map((w) => w.replace(/[^a-z0-9-]/g, ''))
			.filter((w) => w.length >= 3);

		// Fallback to the raw input if every word got filtered out (e.g. "AI", "5G").
		const terms = words.length > 0 ? words : [text.trim().toLowerCase()];
		const escaped = terms.map((w) => w.replace(/'/g, "''"));

		// Search title_full (which carries the full parent chain — e.g. for H01M10/0562 the
		// title_full reads "Secondary cells > Accumulators with non-aqueous electrolyte >
		// Li-accumulators > Rocking-chair batteries > Solid materials"). 95% of rows have a
		// richer title_full than title_en, so this catches concepts inherited from parents.
		// Display title_en in the UI because it's the clean leaf label.
		const matchExprs = escaped
			.map((w) => `(CASE WHEN LOWER(title_full) LIKE '%${w}%' THEN 1 ELSE 0 END)`)
			.join(' + ');
		const orExprs = escaped.map((w) => `LOWER(title_full) LIKE '%${w}%'`).join(' OR ');

		try {
			cpcSuggestions = await runQuery(`
				SELECT symbol, title_en, (${matchExprs}) AS match_count
				FROM tls_cpc_hierarchy
				WHERE (${orExprs})
				  AND CAST(level AS INTEGER) >= 4
				ORDER BY match_count DESC, CAST(level AS INTEGER), LENGTH(symbol)
				LIMIT 30
			`);
			elapsed = Math.round(performance.now() - t0);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	function pickSuggestion(symbol: string) {
		query = symbol;
		cpcSuggestions = [];
		search();
	}

	async function search() {
		const cpc = query.trim().toUpperCase();
		if (!cpc) return;

		loading = true;
		errorMsg = '';
		topApplicants = [];
		trend = [];
		cpcSuggestions = [];
		const t0 = performance.now();
		const escaped = cpc.replace(/'/g, "''");

		// Optional applicant filter from context
		const applicantJoin = hasApplicantFilter
			? `JOIN tls207_pers_appln pa_ctx ON a.appln_id = pa_ctx.appln_id AND pa_ctx.applt_seq_nr > 0
			   JOIN tls206_person p_ctx ON pa_ctx.person_id = p_ctx.person_id`
			: '';
		const applicantWhere = hasApplicantFilter
			? `AND ${nameWhereClause(ctx, 'p_ctx')}`
			: '';

		try {
			const [applicantData, trendData] = await Promise.all([
				runQuery(`
					SELECT p.person_name AS name,
						   p.person_ctry_code AS country,
						   COUNT(DISTINCT a.docdb_family_id) AS families
					FROM tls224_appln_cpc c
					JOIN tls201_appln a ON c.appln_id = a.appln_id
					JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
					JOIN tls206_person p ON pa.person_id = p.person_id
					${applicantJoin}
					WHERE c.cpc_class_symbol LIKE '${escaped}%'
					  AND pa.applt_seq_nr > 0
					  ${applicantWhere}
					GROUP BY p.person_name, p.person_ctry_code
					ORDER BY families DESC
					LIMIT 20
				`),
				runQuery(`
					SELECT a.appln_filing_year AS year,
						   COUNT(DISTINCT a.docdb_family_id) AS families
					FROM tls224_appln_cpc c
					JOIN tls201_appln a ON c.appln_id = a.appln_id
					${applicantJoin}
					WHERE c.cpc_class_symbol LIKE '${escaped}%'
					  AND a.appln_filing_year BETWEEN 1990 AND 2024
					  ${applicantWhere}
					GROUP BY a.appln_filing_year
					ORDER BY year
				`)
			]);

			topApplicants = applicantData;
			trend = trendData;
			elapsed = Math.round(performance.now() - t0);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Technology Search | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-2xl">Technology Search</Card.Title>
			<Card.Description>
				Type a CPC code (<strong>H01M</strong>) or a description (<strong>battery</strong>) — both work.
				{#if hasApplicantFilter}
					<div class="mt-2 flex items-center gap-2">
						<span class="text-xs text-muted-foreground">Filtered to:</span>
						<ConsolidatedNames {ctx} />
						<a href="{base}/technology" class="text-xs underline">(clear)</a>
					</div>
				{/if}
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="flex gap-3">
				<label class="sr-only" for="cpc-query">CPC code or description</label>
				<input
					id="cpc-query"
					type="text"
					bind:value={query}
					placeholder="e.g. H01M or battery"
					class="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm
						   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
				/>
				<Button type="submit" disabled={loading || !query.trim()}>
					{loading ? 'Searching...' : 'Search'}
				</Button>
			</form>
		</Card.Content>
	</Card.Root>

	{#if cpcSuggestions.length > 0}
		<Card.Root>
			<Card.Header>
				<Card.Title class="text-base">Matching CPC codes</Card.Title>
				<Card.Description>{cpcSuggestions.length} result{cpcSuggestions.length === 1 ? '' : 's'} · click one to see top applicants</Card.Description>
			</Card.Header>
			<Card.Content class="p-0">
				<ul class="divide-y">
					{#each cpcSuggestions as suggestion}
						<li>
							<button
								type="button"
								class="w-full text-left px-4 py-2.5 text-sm hover:bg-muted/50 transition-colors flex items-baseline gap-3"
								onclick={() => pickSuggestion(suggestion.symbol)}
							>
								<span class="font-mono font-semibold text-[var(--mtc-blue)] shrink-0 min-w-[5rem]">{suggestion.symbol}</span>
								<span class="text-muted-foreground">{suggestion.title_en}</span>
							</button>
						</li>
					{/each}
				</ul>
			</Card.Content>
		</Card.Root>
	{:else if !loading && !errorMsg && query && !isCpcCode(query) && topApplicants.length === 0 && trend.length === 0 && elapsed > 0}
		<Card.Root>
			<Card.Content class="py-6 text-sm text-muted-foreground text-center">
				No CPC codes match <span class="font-medium text-foreground">"{query}"</span>. Try simpler or fewer words, or enter a CPC code directly (e.g. <code class="font-mono">H01M</code>).
			</Card.Content>
		</Card.Root>
	{/if}

	{#if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">
			{errorMsg}
		</div>
	{/if}

	{#if trend.length > 0}
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<div>
					<Card.Title>
						Filing Trend:
						<a
							href="https://patentclassificationexplorer.com/cpc/{query.trim().toLowerCase().replace(/[\s/]+/g, '-')}"
							target="_blank"
							rel="noopener"
							class="text-[var(--mtc-blue)] hover:underline"
						>{query.trim().toUpperCase()} ↗</a>
						{#if hasApplicantFilter}
							<Badge variant="secondary" class="ml-2 text-xs">{ctx.label}</Badge>
						{/if}
					</Card.Title>
					<Card.Description>{elapsed}ms</Card.Description>
				</div>
				<Button variant="outline" size="sm" onclick={() => downloadCsv(trend, `${query.trim()}_trend.csv`)}>
					Export CSV
				</Button>
			</Card.Header>
			<Card.Content>
				<div class="h-[300px]">
					<BarChart
						data={trend}
						x="year"
						y="families"
						height={300}
						props={{
							bars: { fill: 'var(--mtc-blue)', radius: 3 },
						}}
					/>
				</div>
			</Card.Content>
		</Card.Root>
	{/if}

	{#if topApplicants.length > 0}
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<Card.Title>
					Top Applicants
					{#if hasApplicantFilter}
						<Badge variant="secondary" class="ml-2 text-xs">filtered</Badge>
					{/if}
				</Card.Title>
				<Button variant="outline" size="sm" onclick={() => downloadCsv(topApplicants, `${query.trim()}_applicants.csv`)}>
					Export CSV
				</Button>
			</Card.Header>
			<Card.Content class="p-0">
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head>Applicant</Table.Head>
							<Table.Head>Country</Table.Head>
							<Table.Head class="text-right">Families</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each topApplicants as row}
							<Table.Row>
								<Table.Cell>
									<a
										href="{base}/applicant?name={encodeURIComponent(row.name)}&country={encodeURIComponent(row.country)}&cpc={encodeURIComponent(query.trim().toUpperCase())}"
										class="font-medium text-[var(--mtc-blue)] hover:underline"
									>
										{row.name}
									</a>
								</Table.Cell>
								<Table.Cell>
									<Badge variant="outline">{row.country}</Badge>
								</Table.Cell>
								<Table.Cell class="text-right tabular-nums font-medium">
									{row.families.toLocaleString()}
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</Card.Content>
		</Card.Root>
	{/if}
</div>
