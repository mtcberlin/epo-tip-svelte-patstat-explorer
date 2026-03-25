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
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);

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
		const cpc = query.trim().toUpperCase();
		if (!cpc) return;

		loading = true;
		errorMsg = '';
		topApplicants = [];
		trend = [];
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
				Search by CPC classification code. Shows top applicants and filing trends for the technology field.
				{#if hasApplicantFilter}
					<div class="mt-2 flex items-center gap-2">
						<span class="text-xs text-muted-foreground">Filtered to:</span>
						<ConsolidatedNames {ctx} />
						<a href="{base}/technology" class="text-xs underline">(clear)</a>
					</div>
				{/if}
			</Card.Description>
			<details class="mt-2 text-xs text-muted-foreground">
				<summary class="cursor-pointer hover:text-foreground transition-colors">What are CPC codes?</summary>
				<p class="mt-1.5 leading-relaxed">
					The Cooperative Patent Classification (CPC) organizes patents into technology areas.
					Enter a code prefix like <strong>H01M</strong> (batteries), <strong>A61K</strong> (medical preparations),
					or <strong>B60W</strong> (autonomous driving). Shorter prefixes (e.g. <strong>H01</strong>) cover broader fields.
				</p>
			</details>
		</Card.Header>
		<Card.Content>
			<form onsubmit={(e) => { e.preventDefault(); search(); }} class="flex gap-3">
				<label class="sr-only" for="cpc-query">CPC code</label>
				<input
					id="cpc-query"
					type="text"
					bind:value={query}
					placeholder="e.g. H01B (cables, conductors), A61K (medical preparations)..."
					class="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm
						   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
				/>
				<Button type="submit" disabled={loading || !query.trim()}>
					{loading ? 'Searching...' : 'Search'}
				</Button>
			</form>
		</Card.Content>
	</Card.Root>

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
