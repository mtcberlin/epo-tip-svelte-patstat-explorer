<script lang="ts">
	import { base } from '$app/paths';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Separator } from '$lib/components/ui/separator';
	import { BarChart } from 'layerchart';
	import { downloadCsv } from '$lib/csv';

	// --- Types ---
	interface Applicant {
		name: string;
		country: string;
		families: number;
	}

	// --- Search state ---
	let query = $state('');
	let yearFrom = $state(1970);
	let yearTo = $state(2024);
	let applicants = $state<Applicant[]>([]);
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);

	// --- Selection state ---
	let selected = $state<Set<string>>(new Set());
	let parentName = $state('');
	let customParent = $state('');
	let useCustomParent = $state(false);

	// --- Preview ---
	let previewTrend = $state<{ year: number; families: number }[]>([]);
	let previewLoading = $state(false);

	// --- Derived ---
	let previewTotal = $derived(
		applicants.filter((a) => selected.has(a.name)).reduce((sum, a) => sum + a.families, 0)
	);
	let effectiveParent = $derived(useCustomParent && customParent.trim() ? customParent.trim() : parentName);
	let selectedNames = $derived([...selected]);
	let hasSelection = $derived(selected.size > 0);

	// --- Data fetching ---
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
		if (!query.trim()) return;
		loading = true;
		errorMsg = '';
		applicants = [];
		selected = new Set();
		parentName = '';
		previewTrend = [];
		const t0 = performance.now();

		const escaped = query.trim().replace(/'/g, "''").toUpperCase();
		const yearFilter = (yearFrom > 1970 || yearTo < 2024)
			? `AND a.appln_filing_year BETWEEN ${yearFrom} AND ${yearTo}` : '';

		try {
			applicants = await runQuery(`
				SELECT p.person_name AS name,
					   p.person_ctry_code AS country,
					   COUNT(DISTINCT a.docdb_family_id) AS families
				FROM tls206_person p
				JOIN tls207_pers_appln pa ON p.person_id = pa.person_id
				JOIN tls201_appln a ON pa.appln_id = a.appln_id
				WHERE pa.applt_seq_nr > 0
					AND UPPER(p.person_name) LIKE '${escaped}%'
					${yearFilter}
				GROUP BY p.person_name, p.person_ctry_code
				ORDER BY families DESC
				LIMIT 200
			`);
			elapsed = Math.round(performance.now() - t0);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	// --- Selection helpers ---
	function toggleName(name: string) {
		const next = new Set(selected);
		if (next.has(name)) next.delete(name);
		else next.add(name);
		selected = next;
		if (!useCustomParent && selected.size > 0) {
			const top = applicants.filter((a) => selected.has(a.name)).sort((a, b) => b.families - a.families)[0];
			if (top) parentName = top.name;
		}
	}

	function selectAll() {
		selected = new Set(applicants.map((a) => a.name));
		if (applicants.length > 0) parentName = applicants[0].name;
	}

	function selectNone() {
		selected = new Set();
		parentName = '';
		previewTrend = [];
	}

	function setAsParent(name: string) {
		parentName = name;
		useCustomParent = false;
		if (!selected.has(name)) toggleName(name);
	}

	// --- Auto-suggest ---
	const LEGAL_SUFFIXES = new Set([
		'AG', 'GMBH', 'GMBH&CO', 'INC', 'LTD', 'LIMITED', 'CO', 'CORP', 'CORPORATION',
		'SA', 'NV', 'BV', 'SE', 'PLC', 'LLC', 'KG', 'OHG', 'SRL', 'SPA', 'AB', 'AS',
		'OY', 'PTY', 'LP', 'LLP', 'AKTIENGESELLSCHAFT', 'GESELLSCHAFT', 'MBH',
		'KABUSHIKI', 'KAISHA', 'KK', 'COMPANY', 'INDUSTRIES', 'INDUSTRIAL',
		'ELECTRONICS', 'ELECTRIC', 'INTERNATIONAL', 'HOLDINGS', 'GROUP', 'GLOBAL',
		'OF', 'THE', 'AND', 'DE', 'DER', 'DES', 'ET', 'UND',
	]);

	function coreNameOf(name: string): string {
		const words = name.toUpperCase().replace(/[.,()]/g, ' ').split(/\s+/).filter(Boolean);
		const core: string[] = [];
		for (const w of words) {
			if (LEGAL_SUFFIXES.has(w)) continue;
			core.push(w);
			if (core.length === 1) break;
		}
		return core.join(' ');
	}

	function autoSuggestFor(anchorName: string) {
		const targetCore = coreNameOf(anchorName);
		if (!targetCore) return;
		const similar = new Set(
			applicants.filter((a) => coreNameOf(a.name) === targetCore).map((a) => a.name)
		);
		selected = similar;
		parentName = anchorName;
		useCustomParent = false;
	}

	function autoSuggest() {
		if (applicants.length === 0) return;
		const anchor = parentName || applicants[0].name;
		autoSuggestFor(anchor);
	}

	// --- Preview ---
	async function loadPreview() {
		if (selectedNames.length === 0) return;
		previewLoading = true;
		try {
			const inClause = selectedNames.map((n) => `'${n.replace(/'/g, "''")}'`).join(',');
			previewTrend = await runQuery(`
				SELECT a.appln_filing_year AS year,
					   COUNT(DISTINCT a.docdb_family_id) AS families
				FROM tls201_appln a
				JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
				JOIN tls206_person p ON pa.person_id = p.person_id
				WHERE p.person_name IN (${inClause})
				  AND pa.applt_seq_nr > 0
				  AND a.appln_filing_year BETWEEN 1990 AND 2024
				GROUP BY a.appln_filing_year
				ORDER BY year
			`);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		}
		previewLoading = false;
	}

	// --- Navigation ---
	function goToApplicant(name: string, country: string) {
		window.location.href = `${base}/applicant?name=${encodeURIComponent(name)}&country=${encodeURIComponent(country)}`;
	}

	function analyzeConsolidated() {
		const params = new URLSearchParams();
		params.set('names', selectedNames.join('|||'));
		params.set('label', effectiveParent);
		window.location.href = `${base}/applicant?${params.toString()}`;
	}
</script>

<svelte:head>
	<title>Applicant Search | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<!-- Search bar -->
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-2xl">Applicant Search</Card.Title>
			<Card.Description>
				Search by name, then click to analyse a single applicant or select multiple to consolidate.
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<form onsubmit={(e) => { e.preventDefault(); search(); }} class="space-y-3">
				<div class="flex gap-3">
					<label class="sr-only" for="applicant-query">Applicant name</label>
					<input
						id="applicant-query"
						type="text"
						bind:value={query}
						placeholder="e.g. Siemens, Samsung, BASF..."
						class="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm
							   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
					/>
					<Button type="submit" disabled={loading || !query.trim()}>
						{loading ? 'Searching...' : 'Search'}
					</Button>
				</div>
				<div class="flex items-center gap-2 text-sm">
					<label for="search-year-from" class="text-muted-foreground">Filing years:</label>
					<input id="search-year-from" type="number" bind:value={yearFrom} min={1970} max={2025}
						class="w-20 rounded-md border border-input bg-background px-2 py-1 text-sm" />
					<span class="text-muted-foreground">&ndash;</span>
					<input id="search-year-to" type="number" bind:value={yearTo} min={1970} max={2025}
						class="w-20 rounded-md border border-input bg-background px-2 py-1 text-sm" />
				</div>
			</form>
		</Card.Content>
	</Card.Root>

	{#if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">{errorMsg}</div>
	{/if}

	{#if applicants.length > 0}
		<div class="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-start">
			<!-- Left: Results list with checkboxes -->
			<Card.Root>
				<Card.Header>
					<div class="flex items-center justify-between">
						<div>
							<Card.Title>
								{applicants.length} results
								{#if hasSelection}
									<Badge class="ml-2">{selected.size} selected</Badge>
								{/if}
							</Card.Title>
							<Card.Description>
								{elapsed}ms &middot; Click name to analyse, use checkboxes to consolidate
							</Card.Description>
						</div>
						<div class="flex gap-2">
							<Button variant="outline" size="sm" onclick={autoSuggest}>Auto-suggest</Button>
							<Button variant="ghost" size="sm" onclick={selectAll}>All</Button>
							<Button variant="ghost" size="sm" onclick={selectNone}>None</Button>
							<Button variant="ghost" size="sm" onclick={() => downloadCsv(applicants, 'applicants.csv')}>CSV</Button>
						</div>
					</div>
				</Card.Header>
				<Card.Content class="p-0">
					<div class="max-h-[calc(100vh-320px)] overflow-y-auto" role="listbox" aria-label="Applicant names" aria-multiselectable="true">
						{#each applicants as applicant}
							{@const isSelected = selected.has(applicant.name)}
							{@const isParent = !useCustomParent && parentName === applicant.name}
							<div
								role="option"
								aria-selected={isSelected}
								class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors
									hover:bg-muted/50
									{isSelected ? 'bg-muted/30' : ''}
									{isParent ? 'border-l-2 border-[var(--mtc-blue)]' : 'border-l-2 border-transparent'}"
							>
								<button onclick={() => toggleName(applicant.name)} class="shrink-0" aria-label="Select {applicant.name}">
									<Checkbox checked={isSelected} tabindex={-1} />
								</button>
								<a
									href="{base}/applicant?name={encodeURIComponent(applicant.name)}&country={encodeURIComponent(applicant.country)}"
									class="flex-1 min-w-0 hover:underline"
								>
									<div class="flex items-center gap-2">
										<span class="truncate font-medium">{applicant.name}</span>
										{#if isParent}
											<Badge variant="default" class="text-[10px] px-1.5 py-0">PARENT</Badge>
										{/if}
									</div>
									<span class="text-xs text-muted-foreground">{applicant.country} &middot; {applicant.families.toLocaleString()} families</span>
								</a>
								<div class="flex gap-2 shrink-0">
									{#if !isParent}
										<button
											onclick={() => autoSuggestFor(applicant.name)}
											class="text-[10px] text-[var(--mtc-blue)] hover:text-foreground underline"
										>
											suggest
										</button>
									{/if}
									{#if isSelected && !isParent}
										<button
											onclick={() => setAsParent(applicant.name)}
											class="text-[10px] text-muted-foreground hover:text-foreground underline"
										>
											parent
										</button>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</Card.Content>
			</Card.Root>

			<!-- Right: Consolidation sidebar (appears when selection exists) -->
			<div class="space-y-4 {hasSelection ? '' : 'hidden lg:block'}">
				{#if hasSelection}
					<!-- Parent name config -->
					<Card.Root>
						<Card.Header>
							<Card.Title class="text-base">Consolidate &amp; Analyse</Card.Title>
						</Card.Header>
						<Card.Content class="space-y-3">
							<div class="space-y-2 text-sm">
								<div class="flex justify-between">
									<span class="text-muted-foreground">Names grouped</span>
									<span class="font-medium">{selected.size}</span>
								</div>
								<div class="flex justify-between">
									<span class="text-muted-foreground">Total families</span>
									<span class="font-medium tabular-nums">{previewTotal.toLocaleString()}</span>
								</div>
							</div>

							<Separator />

							<label class="flex items-center gap-2 text-sm">
								<input type="radio" name="parent-mode" checked={!useCustomParent}
									onchange={() => { useCustomParent = false; }} class="accent-[var(--mtc-blue)]" />
								Use parent: <span class="font-medium truncate">{parentName || '—'}</span>
							</label>
							<label class="flex items-center gap-2 text-sm">
								<input type="radio" name="parent-mode" checked={useCustomParent}
									onchange={() => { useCustomParent = true; }} class="accent-[var(--mtc-blue)]" />
								Custom name
							</label>
							{#if useCustomParent}
								<input type="text" bind:value={customParent} placeholder="e.g. Siemens Group"
									class="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm
										focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none" />
							{/if}

							<Separator />

							<div class="flex flex-col gap-2">
								<Button onclick={loadPreview} disabled={previewLoading} variant="outline" class="w-full">
									{previewLoading ? 'Loading...' : 'Preview Trend'}
								</Button>
								<Button onclick={analyzeConsolidated} disabled={!effectiveParent} class="w-full">
									Analyse {selected.size > 1 ? 'Consolidated' : 'Selected'}
								</Button>
							</div>
						</Card.Content>
					</Card.Root>

					<!-- Selected names -->
					<Card.Root>
						<Card.Header>
							<Card.Title class="text-base">Selected Names</Card.Title>
						</Card.Header>
						<Card.Content class="p-0">
							<div class="max-h-[200px] overflow-y-auto">
								{#each applicants.filter((a) => selected.has(a.name)) as a}
									<div class="flex items-center justify-between px-4 py-1.5 text-xs">
										<span class="truncate {a.name === parentName && !useCustomParent ? 'font-semibold' : ''}">
											{a.name}
										</span>
										<span class="tabular-nums text-muted-foreground ml-2">{a.families.toLocaleString()}</span>
									</div>
								{/each}
							</div>
						</Card.Content>
					</Card.Root>

					<!-- Preview chart -->
					{#if previewTrend.length > 0}
						<Card.Root>
							<Card.Header class="flex-row items-center justify-between">
								<Card.Title class="text-base">Consolidated Trend</Card.Title>
								<Button variant="outline" size="sm"
									onclick={() => downloadCsv(previewTrend, `${effectiveParent}_trend.csv`)}>CSV</Button>
							</Card.Header>
							<Card.Content>
								<div class="h-[180px]">
									<BarChart data={previewTrend} x="year" y="families" height={180}
										props={{ bars: { fill: 'var(--mtc-blue)', radius: 2 } }} />
								</div>
							</Card.Content>
						</Card.Root>
					{/if}
				{:else}
					<Card.Root>
						<Card.Content class="py-6 text-center text-sm text-muted-foreground">
							Use checkboxes to select multiple names for consolidation, or click a name to analyse directly.
						</Card.Content>
					</Card.Root>
				{/if}
			</div>
		</div>
	{:else if !loading && !errorMsg && query}
		<p class="text-sm text-muted-foreground">No results found.</p>
	{/if}
</div>
