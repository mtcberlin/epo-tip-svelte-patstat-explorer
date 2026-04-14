<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import { BarChart } from 'layerchart';
	import { downloadCsv } from '$lib/csv';
	import { parseContext, contextToParams, nameWhereClause, type AnalysisContext } from '$lib/context';
	import ConsolidatedNames from '$lib/components/consolidated-names.svelte';

	// --- Context ---
	const ctx = $derived(parseContext(page.url.searchParams));
	const nameFilter = $derived(nameWhereClause(ctx));
	const ctxParams = $derived(contextToParams(ctx));
	const isConsolidated = $derived(ctx.names.length > 1);

	// --- Data ---
	let trend = $state<{ year: number; families: number }[]>([]);
	let jurisdictions = $state<{ authority: string; families: number }[]>([]);
	let cpcCodes = $state<{ cpc: string; families: number }[]>([]);
	let loading = $state({ trend: false, jurisdictions: false, cpc: false });
	let errors = $state({ trend: '', jurisdictions: '', cpc: '' });

	async function query(sql: string): Promise<any[]> {
		const res = await fetch(`${base}/api/query`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ sql })
		});
		if (!res.ok) throw new Error(await res.text());
		const data = await res.json();
		return data.rows ?? data;
	}

	async function loadTrend() {
		loading.trend = true;
		errors.trend = '';
		try {
			trend = await query(`
				SELECT a.appln_filing_year AS year,
					   COUNT(DISTINCT a.docdb_family_id) AS families
				FROM tls201_appln a
				JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
				JOIN tls206_person p ON pa.person_id = p.person_id
				WHERE ${nameFilter}
				  AND pa.applt_seq_nr > 0
				  AND a.appln_filing_year BETWEEN 1990 AND 2024
				GROUP BY a.appln_filing_year
				ORDER BY year
			`);
		} catch (e) { errors.trend = String(e); }
		loading.trend = false;
	}

	async function loadJurisdictions() {
		loading.jurisdictions = true;
		errors.jurisdictions = '';
		try {
			jurisdictions = await query(`
				SELECT a.appln_auth AS authority,
					   COUNT(DISTINCT a.docdb_family_id) AS families
				FROM tls201_appln a
				JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
				JOIN tls206_person p ON pa.person_id = p.person_id
				WHERE ${nameFilter}
				  AND pa.applt_seq_nr > 0
				GROUP BY a.appln_auth
				ORDER BY families DESC
				LIMIT 15
			`);
		} catch (e) { errors.jurisdictions = String(e); }
		loading.jurisdictions = false;
	}

	async function loadCpc() {
		loading.cpc = true;
		errors.cpc = '';
		try {
			cpcCodes = await query(`
				SELECT SUBSTR(c.cpc_class_symbol, 1, 4) AS cpc,
					   COUNT(DISTINCT a.docdb_family_id) AS families
				FROM tls201_appln a
				JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
				JOIN tls206_person p ON pa.person_id = p.person_id
				JOIN tls224_appln_cpc c ON a.appln_id = c.appln_id
				WHERE ${nameFilter}
				  AND pa.applt_seq_nr > 0
				GROUP BY cpc
				ORDER BY families DESC
				LIMIT 15
			`);
		} catch (e) { errors.cpc = String(e); }
		loading.cpc = false;
	}

	$effect(() => {
		if (ctx.names.length > 0) {
			loadTrend();
			loadJurisdictions();
			loadCpc();
		}
	});
</script>

<svelte:head>
	<title>{ctx.label} | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header with context info -->
	<Card.Root>
		<Card.Header>
			<div class="flex items-start justify-between gap-4">
				<div>
					<Card.Title class="text-2xl">{ctx.label}</Card.Title>
					<Card.Description class="mt-1">
						<div class="flex flex-wrap items-center gap-2">
							<ConsolidatedNames {ctx} />
							{#if page.url.searchParams.get('country')}
								<Badge variant="outline">{page.url.searchParams.get('country')}</Badge>
							{/if}
						</div>
					</Card.Description>
				</div>
				<Button variant="outline" size="sm" href="{base}/search">
					&larr; Search
				</Button>
			</div>
		</Card.Header>
	</Card.Root>

	<!-- Analysis tabs -->
	<Tabs.Root value="trend">
		<Tabs.List>
			<Tabs.Trigger value="trend">Filing Trend</Tabs.Trigger>
			<Tabs.Trigger value="jurisdictions">Jurisdictions</Tabs.Trigger>
			<Tabs.Trigger value="technology">Technology</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content value="trend">
			<Card.Root>
				<Card.Header class="flex-row items-center justify-between">
					<Card.Title>Filing Trend by Year</Card.Title>
					{#if trend.length > 0}
						<Button variant="outline" size="sm" onclick={() => downloadCsv(trend, `${ctx.label}_trend.csv`)}>
							Export CSV
						</Button>
					{/if}
				</Card.Header>
				<Card.Content>
					{#if loading.trend}
						<div class="flex items-center gap-2 text-sm text-muted-foreground"><div class="h-3.5 w-3.5 rounded-full border-2 border-[var(--mtc-blue)] border-t-transparent animate-spin"></div>Loading trend data...</div>
					{:else if errors.trend}
						<p class="text-sm text-destructive">{errors.trend}</p>
					{:else if trend.length > 0}
						<div class="h-[350px]">
							<BarChart data={trend} x="year" y="families" height={350}
								props={{ bars: { fill: 'var(--mtc-blue)', radius: 3 } }} />
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No trend data available.</p>
					{/if}
				</Card.Content>
			</Card.Root>
		</Tabs.Content>

		<Tabs.Content value="jurisdictions">
			<Card.Root>
				<Card.Header class="flex-row items-center justify-between">
					<Card.Title>Top Filing Jurisdictions</Card.Title>
					{#if jurisdictions.length > 0}
						<Button variant="outline" size="sm" onclick={() => downloadCsv(jurisdictions, `${ctx.label}_jurisdictions.csv`)}>
							Export CSV
						</Button>
					{/if}
				</Card.Header>
				<Card.Content>
					{#if loading.jurisdictions}
						<div class="flex items-center gap-2 text-sm text-muted-foreground"><div class="h-3.5 w-3.5 rounded-full border-2 border-[var(--mtc-blue)] border-t-transparent animate-spin"></div>Loading jurisdiction data...</div>
					{:else if errors.jurisdictions}
						<p class="text-sm text-destructive">{errors.jurisdictions}</p>
					{:else if jurisdictions.length > 0}
						<div class="h-[400px]">
							<BarChart data={jurisdictions} x="families" y="authority" height={400}
								orientation="horizontal"
								props={{ bars: { fill: 'var(--mtc-navy)', radius: 3 } }} />
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No jurisdiction data available.</p>
					{/if}
				</Card.Content>
			</Card.Root>
		</Tabs.Content>

		<Tabs.Content value="technology">
			<Card.Root>
				<Card.Header class="flex-row items-center justify-between">
					<Card.Title>Top Technology Fields (CPC)</Card.Title>
					{#if cpcCodes.length > 0}
						<Button variant="outline" size="sm" onclick={() => downloadCsv(cpcCodes, `${ctx.label}_cpc.csv`)}>
							Export CSV
						</Button>
					{/if}
				</Card.Header>
				<Card.Content>
					{#if loading.cpc}
						<div class="flex items-center gap-2 text-sm text-muted-foreground"><div class="h-3.5 w-3.5 rounded-full border-2 border-[var(--mtc-blue)] border-t-transparent animate-spin"></div>Loading technology data...</div>
					{:else if errors.cpc}
						<p class="text-sm text-destructive">{errors.cpc}</p>
					{:else if cpcCodes.length > 0}
						<div class="h-[400px]">
							<BarChart data={cpcCodes} x="families" y="cpc" height={400}
								orientation="horizontal"
								props={{ bars: { fill: 'var(--mtc-accent)', radius: 3 } }} />
						</div>
						<Table.Root class="mt-4">
							<Table.Header>
								<Table.Row>
									<Table.Head>CPC Code</Table.Head>
									<Table.Head class="text-right">Families</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each cpcCodes as row}
									<Table.Row>
										<Table.Cell>
											<a href="https://patentclassificationexplorer.com/cpc/{row.cpc.toLowerCase().replace(/[\s/]+/g, '-')}"
												target="_blank" rel="noopener"
												class="font-medium text-[var(--mtc-blue)] hover:underline">
												{row.cpc} ↗
											</a>
										</Table.Cell>
										<Table.Cell class="text-right tabular-nums">{row.families.toLocaleString()}</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					{:else}
						<p class="text-sm text-muted-foreground">No technology data available.</p>
					{/if}
				</Card.Content>
			</Card.Root>
		</Tabs.Content>
	</Tabs.Root>
</div>
