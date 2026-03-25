<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { downloadCsv } from '$lib/csv';
	import { parseContext, nameWhereClause } from '$lib/context';
	import PatentDetailSheet from '$lib/components/patent-detail-sheet.svelte';
	import ConsolidatedNames from '$lib/components/consolidated-names.svelte';

	const ctx = $derived(parseContext(page.url.searchParams));
	const hasApplicantFilter = $derived(ctx.names.length > 0);

	interface PatentResult {
		appln_id: number;
		appln_auth: string;
		appln_nr: string;
		appln_filing_year: number;
		docdb_family_id: number;
		title: string;
		abstract_excerpt: string;
		applicant: string;
	}

	let query = $state('');
	let searchIn = $state<'title' | 'both'>('both');
	let yearFrom = $state(2015);
	let yearTo = $state(2024);
	let results = $state<PatentResult[]>([]);
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);
	let detailOpen = $state(false);
	let detailApplnId = $state<number | null>(null);

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

	async function search() {
		const q = query.trim();
		if (!q) return;

		loading = true;
		errorMsg = '';
		results = [];
		const t0 = performance.now();
		const escaped = q.replace(/'/g, "''").toUpperCase();

		// Build WHERE clause for text matching
		const titleMatch = `UPPER(t.appln_title) LIKE '%${escaped}%'`;
		const abstractMatch = `UPPER(ab.appln_abstract) LIKE '%${escaped}%'`;
		const textWhere = searchIn === 'title' ? titleMatch : `(${titleMatch} OR ${abstractMatch})`;

		// Optional applicant filter from context
		const applicantJoin = hasApplicantFilter
			? `JOIN tls207_pers_appln pa_ctx ON a.appln_id = pa_ctx.appln_id AND pa_ctx.applt_seq_nr > 0
			   JOIN tls206_person p_ctx ON pa_ctx.person_id = p_ctx.person_id`
			: '';
		const applicantWhere = hasApplicantFilter
			? `AND ${nameWhereClause(ctx, 'p_ctx')}`
			: '';

		try {
			results = await runQuery(`
				SELECT DISTINCT
					a.appln_id,
					a.appln_auth,
					a.appln_nr,
					a.appln_filing_year,
					a.docdb_family_id,
					t.appln_title AS title,
					SUBSTR(ab.appln_abstract, 1, 250) AS abstract_excerpt,
					p.person_name AS applicant
				FROM tls201_appln a
				JOIN tls202_appln_title t ON a.appln_id = t.appln_id
				LEFT JOIN tls203_appln_abstr ab ON a.appln_id = ab.appln_id
				LEFT JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id AND pa.applt_seq_nr = 1
				LEFT JOIN tls206_person p ON pa.person_id = p.person_id
				${applicantJoin}
				WHERE ${textWhere}
				  AND t.appln_title_lg = 'en'
				  AND a.appln_filing_year BETWEEN ${yearFrom} AND ${yearTo}
				  ${applicantWhere}
				ORDER BY a.appln_filing_year DESC
				LIMIT 50
			`);
			elapsed = Math.round(performance.now() - t0);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	function highlight(text: string | null, term: string): string {
		if (!text) return '';
		const re = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
		return text.replace(re, '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>');
	}
</script>

<svelte:head>
	<title>Text Search | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-2xl">Text Search</Card.Title>
			<Card.Description>
				Search patent titles and abstracts by keyword. English-language titles only.
				{#if hasApplicantFilter}
					<div class="mt-2 flex items-center gap-2">
						<span class="text-xs text-muted-foreground">Filtered to:</span>
						<ConsolidatedNames {ctx} />
						<a href="{base}/text-search" class="text-xs underline">(clear)</a>
					</div>
				{/if}
			</Card.Description>
		</Card.Header>
		<Card.Content class="space-y-4">
			<form onsubmit={(e) => { e.preventDefault(); search(); }} class="space-y-3">
				<div class="flex gap-3">
					<label class="sr-only" for="text-query">Search keywords</label>
					<input
						id="text-query"
						type="text"
						bind:value={query}
						placeholder="e.g. battery recycling, mRNA vaccine, autonomous driving..."
						class="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm
							   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
					/>
					<Button type="submit" disabled={loading || !query.trim()}>
						{loading ? 'Searching...' : 'Search'}
					</Button>
				</div>
				<div class="flex flex-wrap items-center gap-4 text-sm">
					<fieldset class="flex items-center gap-3">
						<legend class="sr-only">Search scope</legend>
						<label class="flex items-center gap-1.5">
							<input type="radio" name="scope" value="both" bind:group={searchIn} class="accent-[var(--mtc-blue)]" />
							Title + Abstract
						</label>
						<label class="flex items-center gap-1.5">
							<input type="radio" name="scope" value="title" bind:group={searchIn} class="accent-[var(--mtc-blue)]" />
							Title only
						</label>
					</fieldset>
					<div class="flex items-center gap-2">
						<label for="year-from" class="text-muted-foreground">Years:</label>
						<input id="year-from" type="number" bind:value={yearFrom} min={1970} max={2025}
							class="w-20 rounded-md border border-input bg-background px-2 py-1 text-sm" />
						<span class="text-muted-foreground">&ndash;</span>
						<input id="year-to" type="number" bind:value={yearTo} min={1970} max={2025}
							class="w-20 rounded-md border border-input bg-background px-2 py-1 text-sm" />
					</div>
				</div>
			</form>
		</Card.Content>
	</Card.Root>

	{#if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">{errorMsg}</div>
	{/if}

	{#if results.length > 0}
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<div>
					<Card.Title>{results.length} patents found</Card.Title>
					<Card.Description>{elapsed}ms &middot; max 50 results &middot; Click a patent for details</Card.Description>
				</div>
				<Button variant="outline" size="sm" onclick={() => downloadCsv(results, 'text_search.csv')}>
					Export CSV
				</Button>
			</Card.Header>
			<Card.Content class="space-y-4 p-4">
				{#each results as patent}
					<article
						class="rounded-lg border p-4 space-y-2 hover:bg-muted/30 transition-colors cursor-pointer"
						onclick={() => { detailApplnId = patent.appln_id; detailOpen = true; }}
						onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { detailApplnId = patent.appln_id; detailOpen = true; } }}
						role="button"
						tabindex="0"
					>
						<div class="flex items-start justify-between gap-4">
							<h3 class="font-medium text-sm leading-snug">
								{@html highlight(patent.title, query.trim())}
							</h3>
							<Badge variant="outline" class="shrink-0">{patent.appln_auth}</Badge>
						</div>
						{#if patent.abstract_excerpt}
							<p class="text-xs text-muted-foreground leading-relaxed">
								{@html highlight(patent.abstract_excerpt, query.trim())}
								{#if patent.abstract_excerpt.length >= 250}&hellip;{/if}
							</p>
						{/if}
						<div class="flex flex-wrap gap-3 text-xs text-muted-foreground">
							{#if patent.applicant}
								<a
									href="{base}/applicant?name={encodeURIComponent(patent.applicant)}"
									class="text-[var(--mtc-blue)] hover:underline"
								>
									{patent.applicant}
								</a>
							{/if}
							<span>{patent.appln_filing_year}</span>
							<span>Family {patent.docdb_family_id}</span>
							<span>{patent.appln_auth}{patent.appln_nr}</span>
						</div>
					</article>
				{/each}
			</Card.Content>
		</Card.Root>
	{:else if !loading && !errorMsg && query}
		<p class="text-sm text-muted-foreground">No patents found for "{query}".</p>
	{/if}
</div>

<PatentDetailSheet bind:open={detailOpen} bind:applnId={detailApplnId} />
