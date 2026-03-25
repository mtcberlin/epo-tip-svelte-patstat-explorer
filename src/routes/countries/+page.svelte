<script lang="ts">
	import { base } from '$app/paths';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { LineChart } from 'layerchart';
	import { downloadCsv } from '$lib/csv';

	interface TrendRow {
		year: number;
		families: number;
		country: string;
	}

	let countriesInput = $state('DE, US, CN, JP, KR');
	let cpcFilter = $state('');
	let trend = $state<TrendRow[]>([]);
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);

	const colors: Record<string, string> = {
		DE: '#2d3470', US: '#4a5bc7', CN: '#dc2626', JP: '#059669',
		KR: '#d97706', FR: '#7c3aed', GB: '#0ea5e9', EP: '#6b7280',
		WO: '#94a3b8', IN: '#f97316', CA: '#10b981', AU: '#8b5cf6',
		BR: '#06b6d4', IT: '#ec4899', RU: '#78716c',
	};

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
		const codes = countriesInput
			.toUpperCase()
			.split(/[,;\s]+/)
			.map((s) => s.trim())
			.filter(Boolean);
		if (codes.length === 0) return;

		loading = true;
		errorMsg = '';
		trend = [];
		const t0 = performance.now();
		const inClause = codes.map((c) => `'${c}'`).join(',');

		const cpcJoin = cpcFilter.trim()
			? `JOIN tls224_appln_cpc c ON a.appln_id = c.appln_id`
			: '';
		const cpcWhere = cpcFilter.trim()
			? `AND c.cpc_class_symbol LIKE '${cpcFilter.trim().toUpperCase().replace(/'/g, "''")}%'`
			: '';

		try {
			trend = await runQuery(`
				SELECT a.appln_auth AS country,
					   a.appln_filing_year AS year,
					   COUNT(DISTINCT a.docdb_family_id) AS families
				FROM tls201_appln a
				${cpcJoin}
				WHERE a.appln_auth IN (${inClause})
				  AND a.appln_filing_year BETWEEN 2000 AND 2024
				  ${cpcWhere}
				GROUP BY a.appln_auth, a.appln_filing_year
				ORDER BY country, year
			`);
			elapsed = Math.round(performance.now() - t0);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	// Group data by country for the multi-series LineChart
	let countries = $derived([...new Set(trend.map((r) => r.country))].sort());
</script>

<svelte:head>
	<title>Country Comparison | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-2xl">Country Comparison</Card.Title>
			<Card.Description>
				Compare patent filing trends across countries. Optionally filter by CPC technology field.
			</Card.Description>
		</Card.Header>
		<Card.Content class="space-y-4">
			<form onsubmit={(e) => { e.preventDefault(); search(); }} class="space-y-3">
				<div class="flex gap-3">
					<label class="sr-only" for="countries-input">Country codes</label>
					<input
						id="countries-input"
						type="text"
						bind:value={countriesInput}
						placeholder="e.g. DE, US, CN, JP, KR"
						class="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm
							   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
					/>
					<Button type="submit" disabled={loading}>
						{loading ? 'Loading...' : 'Compare'}
					</Button>
				</div>
				<div class="flex items-center gap-2 text-sm">
					<label for="cpc-filter" class="text-muted-foreground">CPC filter (optional):</label>
					<input
						id="cpc-filter"
						type="text"
						bind:value={cpcFilter}
						placeholder="e.g. H01B, A61K"
						class="w-40 rounded-md border border-input bg-background px-2 py-1 text-sm
							   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
					/>
				</div>
			</form>
		</Card.Content>
	</Card.Root>

	{#if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">{errorMsg}</div>
	{/if}

	{#if trend.length > 0}
		<!-- One LineChart per country, stacked -->
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<div>
					<Card.Title>Filing Trends (2000–2024)</Card.Title>
					<Card.Description>
						{elapsed}ms &middot; {countries.length} countries
						{#if cpcFilter.trim()}
							&middot; CPC: <Badge variant="outline">{cpcFilter.trim().toUpperCase()}</Badge>
						{/if}
					</Card.Description>
				</div>
				<Button variant="outline" size="sm" onclick={() => downloadCsv(trend, 'country_comparison.csv')}>
					Export CSV
				</Button>
			</Card.Header>
			<Card.Content>
				<!-- Legend -->
				<div class="flex flex-wrap gap-3 mb-4">
					{#each countries as c}
						<div class="flex items-center gap-1.5 text-xs">
							<div class="h-3 w-3 rounded-full" style="background: {colors[c] ?? '#6b7280'}"></div>
							<span class="font-medium">{c}</span>
						</div>
					{/each}
				</div>

				<!-- Individual charts per country (reliable with LayerChart) -->
				<div class="space-y-4">
					{#each countries as c}
						{@const countryData = trend.filter((r) => r.country === c)}
						<div>
							<div class="text-xs font-semibold text-muted-foreground mb-1 flex items-center gap-2">
								<div class="h-2.5 w-2.5 rounded-full" style="background: {colors[c] ?? '#6b7280'}"></div>
								{c}
								<span class="font-normal">
									({countryData.reduce((s, r) => s + r.families, 0).toLocaleString()} total families)
								</span>
							</div>
							<div class="h-[120px]">
								<LineChart
									data={countryData}
									x="year"
									y="families"
									height={120}
									props={{
										spline: { stroke: colors[c] ?? '#6b7280', 'stroke-width': 2 },
									}}
								/>
							</div>
						</div>
					{/each}
				</div>
			</Card.Content>
		</Card.Root>
	{/if}
</div>
