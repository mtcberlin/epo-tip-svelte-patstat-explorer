<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { downloadCsv } from '$lib/csv';
	import { onMount } from 'svelte';
	import { sankey, sankeyLinkHorizontal, sankeyLeft } from 'd3-sankey';
	import { select } from 'd3-selection';

	// --- Types ---
	interface CitationRow {
		cited_applicant: string;
		tech: string;
		citations: number;
	}

	import { parseContext } from '$lib/context';
	import ConsolidatedNames from '$lib/components/consolidated-names.svelte';

	// --- State ---
	const ctx = $derived(parseContext(page.url.searchParams));
	const initialName = $derived(ctx.label || ctx.names[0] || '');
	let query = $state('');
	let direction = $state<'forward' | 'backward'>('forward');
	let resolvedName = $state('');
	let citationData = $state<CitationRow[]>([]);
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);
	let svgEl: SVGSVGElement;

	$effect(() => {
		if (initialName && !query) query = initialName;
	});

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
		const input = query.trim();
		if (!input) return;

		loading = true;
		errorMsg = '';
		citationData = [];
		resolvedName = '';
		const t0 = performance.now();
		const escaped = input.replace(/'/g, "''");

		try {
			// Resolve name
			const nameResults = await runQuery(`
				SELECT p.person_name AS name,
					   COUNT(DISTINCT a.docdb_family_id) AS families
				FROM tls206_person p
				JOIN tls207_pers_appln pa ON p.person_id = pa.person_id
				JOIN tls201_appln a ON pa.appln_id = a.appln_id
				WHERE pa.applt_seq_nr > 0
				  AND UPPER(p.person_name) LIKE UPPER('${escaped}%')
				GROUP BY p.person_name
				ORDER BY families DESC
				LIMIT 1
			`);

			if (nameResults.length === 0) {
				errorMsg = `No applicant found matching "${input}".`;
				loading = false;
				return;
			}

			const exactName = nameResults[0].name;
			resolvedName = exactName;
			const ee = exactName.replace(/'/g, "''");

			// Build citation query based on direction
			// Forward: who does this applicant cite?
			// Backward: who cites this applicant?
			const isForward = direction === 'forward';

			citationData = await runQuery(`
				SELECT
					p2.person_name AS cited_applicant,
					SUBSTR(cpc.cpc_class_symbol, 1, 4) AS tech,
					COUNT(DISTINCT fc.${isForward ? 'cited_docdb_family_id' : 'docdb_family_id'}) AS citations
				FROM tls206_person p1
				JOIN tls207_pers_appln pa1 ON p1.person_id = pa1.person_id
				JOIN tls201_appln a1 ON pa1.appln_id = a1.appln_id
				JOIN tls228_docdb_fam_citn fc ON a1.docdb_family_id = fc.${isForward ? 'docdb_family_id' : 'cited_docdb_family_id'}
				JOIN tls201_appln a2 ON fc.${isForward ? 'cited_docdb_family_id' : 'docdb_family_id'} = a2.docdb_family_id
				JOIN tls207_pers_appln pa2 ON a2.appln_id = pa2.appln_id
				JOIN tls206_person p2 ON pa2.person_id = p2.person_id
				LEFT JOIN tls224_appln_cpc cpc ON ${isForward ? 'a1' : 'a2'}.appln_id = cpc.appln_id
				WHERE p1.person_name = '${ee}'
				  AND pa1.applt_seq_nr > 0
				  AND pa2.applt_seq_nr > 0
				  AND pa2.invt_seq_nr = 0
				  AND p2.person_name != '${ee}'
				  AND UPPER(p2.person_name) NOT LIKE UPPER('${ee.split(/\s+/)[0]}%')
				GROUP BY p2.person_name, tech
				HAVING citations >= 5
				ORDER BY citations DESC
				LIMIT 200
			`);

			elapsed = Math.round(performance.now() - t0);

			if (citationData.length > 0) {
				requestAnimationFrame(renderSankey);
			}
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	// --- Aggregate for table view ---
	let topApplicants = $derived(
		Object.entries(
			citationData.reduce(
				(acc, r) => {
					acc[r.cited_applicant] = (acc[r.cited_applicant] ?? 0) + r.citations;
					return acc;
				},
				{} as Record<string, number>
			)
		)
			.map(([name, citations]) => ({ name, citations }))
			.sort((a, b) => b.citations - a.citations)
			.slice(0, 20)
	);

	let topTech = $derived(
		Object.entries(
			citationData.reduce(
				(acc, r) => {
					if (r.tech) acc[r.tech] = (acc[r.tech] ?? 0) + r.citations;
					return acc;
				},
				{} as Record<string, number>
			)
		)
			.map(([tech, citations]) => ({ tech, citations }))
			.sort((a, b) => b.citations - a.citations)
			.slice(0, 15)
	);

	// --- Sankey chart ---
	const COLORS = [
		'#2d3470', '#4a5bc7', '#6c7bf0', '#059669', '#d97706',
		'#dc2626', '#7c3aed', '#0ea5e9', '#ec4899', '#f97316',
		'#10b981', '#8b5cf6', '#06b6d4', '#78716c', '#94a3b8',
	];

	function renderSankey() {
		if (!svgEl || citationData.length === 0) return;

		const width = svgEl.clientWidth || 900;
		const height = 550;
		const margin = { top: 10, right: 200, bottom: 10, left: 200 };

		// Build nodes and links for: Applicant → Tech → Cited Applicant (forward)
		// or: Citing Applicant → Tech → Applicant (backward)
		const topN = 10; // top N applicants
		const topT = 8; // top N tech fields
		const topAppNames = new Set(topApplicants.slice(0, topN).map((a) => a.name));
		const topTechCodes = new Set(topTech.slice(0, topT).map((t) => t.tech));

		// Filter data to top applicants and tech
		const filtered = citationData.filter(
			(r) => topAppNames.has(r.cited_applicant) && r.tech && topTechCodes.has(r.tech)
		);

		if (filtered.length === 0) return;

		// Node IDs: "tech:H01L", "app:Samsung..."
		const techNodes = [...topTechCodes].map((t) => `tech:${t}`);
		const appNodes = [...topAppNames].map((n) => `app:${n}`);

		const isForward = direction === 'forward';
		const leftLabel = isForward ? resolvedName : 'Citing Applicants';
		const rightLabel = isForward ? 'Cited Applicants' : resolvedName;

		// Nodes: center (source) → tech fields → target applicants
		const nodeIds = ['center', ...techNodes, ...appNodes];
		const nodeMap = new Map(nodeIds.map((id, i) => [id, i]));

		const nodes = nodeIds.map((id) => ({ id }));

		// Links: center → tech (aggregated), tech → applicant
		const centerToTech = new Map<string, number>();
		const techToApp = new Map<string, number>();

		for (const r of filtered) {
			const tKey = `tech:${r.tech}`;
			centerToTech.set(tKey, (centerToTech.get(tKey) ?? 0) + r.citations);

			const lKey = `${tKey}→app:${r.cited_applicant}`;
			techToApp.set(lKey, (techToApp.get(lKey) ?? 0) + r.citations);
		}

		const links = [
			...[...centerToTech.entries()].map(([target, value]) => ({
				source: nodeMap.get('center')!,
				target: nodeMap.get(target)!,
				value
			})),
			...[...techToApp.entries()].map(([key, value]) => {
				const [src, tgt] = key.split('→');
				return {
					source: nodeMap.get(src)!,
					target: nodeMap.get(tgt)!,
					value
				};
			})
		].filter((l) => l.source !== undefined && l.target !== undefined);

		// Sankey layout
		const sankeyGen = sankey()
			.nodeId((d: any) => nodeIds.indexOf(d.id))
			.nodeAlign(sankeyLeft)
			.nodeWidth(16)
			.nodePadding(14)
			.extent([
				[margin.left, margin.top],
				[width - margin.right, height - margin.bottom]
			]);

		const graph = sankeyGen({
			nodes: nodes.map((d) => ({ ...d })),
			links: links.map((d) => ({ ...d }))
		});

		// Render
		const svg = select(svgEl);
		svg.selectAll('*').remove();
		svg.attr('viewBox', `0 0 ${width} ${height}`);

		// Tech color map
		const techColorMap = new Map(
			[...topTechCodes].map((t, i) => [t, COLORS[i % COLORS.length]])
		);

		// Links
		svg
			.append('g')
			.attr('fill', 'none')
			.selectAll('path')
			.data(graph.links)
			.join('path')
			.attr('d', sankeyLinkHorizontal())
			.attr('stroke', (d: any) => {
				const srcId = graph.nodes[d.source.index ?? d.source]?.id ?? '';
				if (srcId === 'center') {
					const tgtId = graph.nodes[d.target.index ?? d.target]?.id ?? '';
					return techColorMap.get(tgtId.replace('tech:', '')) ?? '#94a3b8';
				}
				return techColorMap.get(srcId.replace('tech:', '')) ?? '#94a3b8';
			})
			.attr('stroke-opacity', 0.35)
			.attr('stroke-width', (d: any) => Math.max(1, d.width));

		// Nodes
		svg
			.append('g')
			.selectAll('rect')
			.data(graph.nodes)
			.join('rect')
			.attr('x', (d: any) => d.x0)
			.attr('y', (d: any) => d.y0)
			.attr('height', (d: any) => Math.max(1, d.y1 - d.y0))
			.attr('width', (d: any) => d.x1 - d.x0)
			.attr('fill', (d: any) => {
				if (d.id === 'center') return 'var(--mtc-navy)';
				if (d.id.startsWith('tech:')) return techColorMap.get(d.id.replace('tech:', '')) ?? '#6b7280';
				return '#94a3b8';
			})
			.attr('rx', 2);

		// Labels
		svg
			.append('g')
			.selectAll('text')
			.data(graph.nodes)
			.join('text')
			.attr('x', (d: any) => (d.x0 < width / 2 ? d.x0 - 6 : d.x1 + 6))
			.attr('y', (d: any) => (d.y0 + d.y1) / 2)
			.attr('dy', '0.35em')
			.attr('text-anchor', (d: any) => (d.x0 < width / 2 ? 'end' : 'start'))
			.attr('font-size', '11px')
			.attr('fill', 'var(--foreground)')
			.text((d: any) => {
				if (d.id === 'center') return resolvedName;
				if (d.id.startsWith('tech:')) return d.id.replace('tech:', '');
				return d.id.replace('app:', '').slice(0, 35);
			});
	}

	// Auto-search if name provided
	$effect(() => {
		if (initialName) search();
	});
</script>

<svelte:head>
	<title>Citation Flow | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-2xl">Citation Flow</Card.Title>
			<Card.Description>
				Analyse patent citation relationships. See who cites whom and through which technologies.
				{#if ctx.names.length > 0}
					<div class="mt-2"><ConsolidatedNames {ctx} /></div>
				{/if}
			</Card.Description>
			<details class="mt-2 text-xs text-muted-foreground">
				<summary class="cursor-pointer hover:text-foreground transition-colors">What am I looking at?</summary>
				<p class="mt-1.5 leading-relaxed">
					A Sankey diagram showing citation flows. <strong>Forward citations</strong> (dependencies):
					which prior art does this applicant reference? <strong>Backward citations</strong> (impact):
					who references this applicant's patents? The middle column shows technology fields (CPC codes).
					Flow thickness = number of citations. Toggle direction with the buttons above.
				</p>
			</details>
		</Card.Header>
		<Card.Content class="space-y-4">
			<form onsubmit={(e) => { e.preventDefault(); search(); }} class="space-y-3">
				<div class="flex gap-3">
					<label class="sr-only" for="citation-query">Applicant name</label>
					<input
						id="citation-query"
						type="text"
						bind:value={query}
						placeholder="e.g. Siemens, Samsung, BASF..."
						class="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm
							   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
					/>
					<Button type="submit" disabled={loading || !query.trim()}>
						{loading ? 'Analysing...' : 'Analyse'}
					</Button>
				</div>
				<fieldset class="flex items-center gap-4 text-sm">
					<legend class="sr-only">Citation direction</legend>
					<label class="flex items-center gap-1.5">
						<input type="radio" name="dir" value="forward" bind:group={direction} class="accent-[var(--mtc-blue)]" />
						Who do they cite? <span class="text-muted-foreground">(dependencies)</span>
					</label>
					<label class="flex items-center gap-1.5">
						<input type="radio" name="dir" value="backward" bind:group={direction} class="accent-[var(--mtc-blue)]" />
						Who cites them? <span class="text-muted-foreground">(impact)</span>
					</label>
				</fieldset>
			</form>
		</Card.Content>
	</Card.Root>

	{#if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">{errorMsg}</div>
	{/if}

	{#if loading}
		<Card.Root>
			<Card.Content class="py-12 space-y-4">
				<div class="flex items-center justify-center gap-3 text-muted-foreground">
					<div class="h-4 w-4 rounded-full border-2 border-[var(--mtc-blue)] border-t-transparent animate-spin"></div>
					<span>Analysing citations... This can take 30-60 seconds for large applicants.</span>
				</div>
				<div class="space-y-2 max-w-md mx-auto">
					<div class="h-3 rounded bg-muted animate-pulse"></div>
					<div class="h-3 rounded bg-muted animate-pulse w-4/5"></div>
					<div class="h-3 rounded bg-muted animate-pulse w-3/5"></div>
				</div>
			</Card.Content>
		</Card.Root>
	{/if}

	{#if citationData.length > 0 && !loading}
		<!-- Sankey -->
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<div>
					<Card.Title>
						{direction === 'forward' ? 'Cites →' : '← Cited by'}:
						{resolvedName}
					</Card.Title>
					<Card.Description>
						{elapsed}ms &middot; Applicant → Technology → {direction === 'forward' ? 'Cited Applicant' : 'Citing Applicant'}
					</Card.Description>
				</div>
			</Card.Header>
			<Card.Content class="p-2">
				<svg
					bind:this={svgEl}
					class="w-full"
					style="height: 550px;"
					role="img"
					aria-label="Citation flow Sankey diagram for {resolvedName}"
				></svg>
			</Card.Content>
		</Card.Root>

		<!-- Tables -->
		<Tabs.Root value="applicants">
			<Tabs.List>
				<Tabs.Trigger value="applicants">
					Top {direction === 'forward' ? 'Cited' : 'Citing'} Applicants
				</Tabs.Trigger>
				<Tabs.Trigger value="tech">Top Technology Fields</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="applicants">
				<Card.Root>
					<Card.Header class="flex-row items-center justify-between">
						<Card.Title>
							{direction === 'forward' ? 'Most Cited Applicants' : 'Top Citing Applicants'}
						</Card.Title>
						<Button variant="outline" size="sm" onclick={() => downloadCsv(topApplicants, `${resolvedName}_citations.csv`)}>
							Export CSV
						</Button>
					</Card.Header>
					<Card.Content class="p-0">
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>Applicant</Table.Head>
									<Table.Head class="text-right">Citations</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each topApplicants as row}
									<Table.Row>
										<Table.Cell>
											<a
												href="{base}/applicant?name={encodeURIComponent(row.name)}"
												class="font-medium hover:underline"
											>
												{row.name}
											</a>
										</Table.Cell>
										<Table.Cell class="text-right tabular-nums font-medium">
											{row.citations.toLocaleString()}
										</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</Card.Content>
				</Card.Root>
			</Tabs.Content>

			<Tabs.Content value="tech">
				<Card.Root>
					<Card.Header class="flex-row items-center justify-between">
						<Card.Title>Technology Fields</Card.Title>
						<Button variant="outline" size="sm" onclick={() => downloadCsv(topTech, `${resolvedName}_citation_tech.csv`)}>
							Export CSV
						</Button>
					</Card.Header>
					<Card.Content class="p-0">
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>CPC Code</Table.Head>
									<Table.Head class="text-right">Citations</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each topTech as row}
									<Table.Row>
										<Table.Cell>
											<a
												href="https://patentclassificationexplorer.com/cpc/{row.tech.toLowerCase().replace(/[\s/]+/g, '-')}"
												target="_blank"
												rel="noopener"
												class="font-medium text-[var(--mtc-blue)] hover:underline"
											>
												{row.tech} ↗
											</a>
										</Table.Cell>
										<Table.Cell class="text-right tabular-nums font-medium">
											{row.citations.toLocaleString()}
										</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</Card.Content>
				</Card.Root>
			</Tabs.Content>
		</Tabs.Root>
	{/if}
</div>
