<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { downloadCsv } from '$lib/csv';
	import { onMount } from 'svelte';
	import {
		forceSimulation,
		forceLink,
		forceManyBody,
		forceCenter,
		forceCollide,
		type SimulationNodeDatum,
		type SimulationLinkDatum
	} from 'd3-force';
	import { select } from 'd3-selection';
	import { drag } from 'd3-drag';
	import { zoom, zoomIdentity } from 'd3-zoom';

	// --- Types ---
	interface CoApplicant {
		co_applicant: string;
		country: string;
		shared_families: number;
	}

	interface GraphNode extends SimulationNodeDatum {
		id: string;
		country: string;
		families: number;
		isCenter: boolean;
	}

	interface GraphLink extends SimulationLinkDatum<GraphNode> {
		weight: number;
	}

	// --- State ---
	import { parseContext } from '$lib/context';
	import ConsolidatedNames from '$lib/components/consolidated-names.svelte';
	const ctx = $derived(parseContext(page.url.searchParams));
	const initialName = $derived(ctx.label || ctx.names[0] || '');
	let query = $state('');
	let coApplicants = $state<CoApplicant[]>([]);
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);
	let svgEl: SVGSVGElement;

	// Initialize query from URL param
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

	let resolvedName = $state('');

	async function search() {
		const input = query.trim();
		if (!input) return;

		loading = true;
		errorMsg = '';
		coApplicants = [];
		resolvedName = '';
		const t0 = performance.now();
		const escaped = input.replace(/'/g, "''");

		try {
			// Step 1: Resolve input to the best-matching exact person_name
			// If it's already exact, this just confirms it. If it's partial, finds the top match.
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
				errorMsg = `No applicant found matching "${input}". Try a more specific name.`;
				loading = false;
				return;
			}

			const exactName = nameResults[0].name;
			resolvedName = exactName;
			const exactEscaped = exactName.replace(/'/g, "''");

			// Step 2: Find co-applicants using the resolved exact name
			coApplicants = await runQuery(`
				SELECT p2.person_name AS co_applicant,
					   p2.person_ctry_code AS country,
					   COUNT(DISTINCT a.docdb_family_id) AS shared_families
				FROM tls207_pers_appln pa1
				JOIN tls206_person p1 ON pa1.person_id = p1.person_id
				JOIN tls207_pers_appln pa2 ON pa1.appln_id = pa2.appln_id
				JOIN tls206_person p2 ON pa2.person_id = p2.person_id
				JOIN tls201_appln a ON pa1.appln_id = a.appln_id
				WHERE p1.person_name = '${exactEscaped}'
				  AND pa1.applt_seq_nr > 0
				  AND pa2.applt_seq_nr > 0
				  AND pa2.invt_seq_nr = 0
				  AND p2.person_name != '${exactEscaped}'
				GROUP BY p2.person_name, p2.person_ctry_code
				ORDER BY shared_families DESC
				LIMIT 30
			`);
			elapsed = Math.round(performance.now() - t0);

			if (coApplicants.length > 0) {
				requestAnimationFrame(() => renderGraph(exactName));
			}
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	// --- Country color palette ---
	const COUNTRY_COLORS: Record<string, string> = {
		DE: '#f59e0b', US: '#3b82f6', CN: '#ef4444', JP: '#10b981',
		KR: '#8b5cf6', FR: '#ec4899', GB: '#06b6d4', NL: '#f97316',
		CH: '#14b8a6', SE: '#a855f7', IT: '#6366f1', CA: '#22c55e',
		IN: '#e11d48', AU: '#0ea5e9', BR: '#84cc16', IL: '#d946ef',
	};
	const DEFAULT_COLOR = '#94a3b8';

	function countryColor(code: string): string {
		return COUNTRY_COLORS[code] ?? DEFAULT_COLOR;
	}

	// --- Force-directed graph ---
	function renderGraph(centerName: string) {
		if (!svgEl || coApplicants.length === 0) return;

		const width = svgEl.clientWidth || 900;
		const height = 700;
		const maxFamilies = Math.max(...coApplicants.map((c) => c.shared_families));

		const nodes: GraphNode[] = [
			{ id: centerName, country: '', families: maxFamilies * 2, isCenter: true },
			...coApplicants.map((c) => ({
				id: c.co_applicant,
				country: c.country,
				families: c.shared_families,
				isCenter: false
			}))
		];

		const links: GraphLink[] = coApplicants.map((c) => ({
			source: centerName,
			target: c.co_applicant,
			weight: c.shared_families
		}));

		const svg = select(svgEl);
		svg.selectAll('*').remove();

		// Defs: glow filter + gradients
		const defs = svg.append('defs');

		// Glow filter for center node
		const glow = defs.append('filter').attr('id', 'glow');
		glow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
		glow.append('feMerge').selectAll('feMergeNode')
			.data(['blur', 'SourceGraphic']).join('feMergeNode')
			.attr('in', (d) => d);

		// Soft glow for other nodes
		const softGlow = defs.append('filter').attr('id', 'soft-glow');
		softGlow.append('feGaussianBlur').attr('stdDeviation', '2.5').attr('result', 'blur');
		softGlow.append('feMerge').selectAll('feMergeNode')
			.data(['blur', 'SourceGraphic']).join('feMergeNode')
			.attr('in', (d) => d);

		const g = svg.append('g');

		// Dark background
		svg.insert('rect', ':first-child')
			.attr('width', '100%').attr('height', '100%')
			.attr('fill', '#0f1729').attr('rx', 8);

		// Zoom
		const zoomBehavior = zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.2, 5])
			.on('zoom', (event) => g.attr('transform', event.transform));
		svg.call(zoomBehavior);

		// Simulation — more spread, stronger repulsion
		const simulation = forceSimulation<GraphNode>(nodes)
			.force('link',
				forceLink<GraphNode, GraphLink>(links)
					.id((d) => d.id)
					.distance((d) => 150 + (1 - d.weight / maxFamilies) * 80)
					.strength((d) => 0.3 + (d.weight / maxFamilies) * 0.7)
			)
			.force('charge', forceManyBody().strength(-500))
			.force('center', forceCenter(width / 2, height / 2))
			.force('collide', forceCollide<GraphNode>().radius((d) => nodeRadius(d) + 12))
			.alphaDecay(0.02);

		// Links — curved paths
		const link = g.append('g')
			.selectAll<SVGPathElement, GraphLink>('path')
			.data(links)
			.join('path')
			.attr('fill', 'none')
			.attr('stroke', (d: any) => countryColor(
				nodes.find((n) => n.id === (typeof d.target === 'string' ? d.target : d.target.id))?.country ?? ''
			))
			.attr('stroke-width', (d) => Math.max(0.5, (d.weight / maxFamilies) * 5))
			.attr('stroke-opacity', (d) => 0.15 + (d.weight / maxFamilies) * 0.35);

		// Node groups
		const nodeGroup = g.append('g')
			.selectAll<SVGGElement, GraphNode>('g')
			.data(nodes)
			.join('g')
			.attr('cursor', 'grab')
			.call(
				drag<SVGGElement, GraphNode>()
					.on('start', (event, d) => {
						if (!event.active) simulation.alphaTarget(0.3).restart();
						d.fx = d.x; d.fy = d.y;
					})
					.on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
					.on('end', (event, d) => {
						if (!event.active) simulation.alphaTarget(0);
						d.fx = null; d.fy = null;
					})
			);

		// Outer ring (glow carrier)
		nodeGroup.append('circle')
			.attr('r', (d) => nodeRadius(d) + 3)
			.attr('fill', (d) => d.isCenter ? '#4a5bc7' : countryColor(d.country))
			.attr('opacity', 0.3)
			.attr('filter', (d) => d.isCenter ? 'url(#glow)' : 'url(#soft-glow)');

		// Inner circle
		nodeGroup.append('circle')
			.attr('r', (d) => nodeRadius(d))
			.attr('fill', (d) => d.isCenter ? '#4a5bc7' : countryColor(d.country))
			.attr('stroke', (d) => d.isCenter ? '#6c7bf0' : 'rgba(255,255,255,0.3)')
			.attr('stroke-width', (d) => d.isCenter ? 3 : 1.5);

		// Family count inside larger nodes
		nodeGroup.filter((d) => nodeRadius(d) >= 12)
			.append('text')
			.text((d) => d.isCenter ? '' : d.families.toLocaleString())
			.attr('text-anchor', 'middle')
			.attr('dy', '0.35em')
			.attr('font-size', '8px')
			.attr('font-weight', '600')
			.attr('fill', 'white')
			.attr('pointer-events', 'none');

		// Labels
		const label = g.append('g')
			.selectAll<SVGTextElement, GraphNode>('text')
			.data(nodes)
			.join('text')
			.attr('text-anchor', 'middle')
			.attr('dy', (d) => nodeRadius(d) + 16)
			.attr('pointer-events', 'none');

		// Name line
		label.append('tspan')
			.text((d) => truncate(d.id, d.isCenter ? 40 : 28))
			.attr('x', 0)
			.attr('font-size', (d) => d.isCenter ? '13px' : '9px')
			.attr('font-weight', (d) => d.isCenter ? '700' : '500')
			.attr('fill', (d) => d.isCenter ? '#e2e8f0' : '#94a3b8');

		// Country badge line
		label.filter((d) => !d.isCenter && d.country)
			.append('tspan')
			.text((d) => d.country)
			.attr('x', 0)
			.attr('dy', '1.1em')
			.attr('font-size', '8px')
			.attr('fill', (d) => countryColor(d.country))
			.attr('font-weight', '600');

		// Hover effects
		nodeGroup
			.on('mouseover', function (event, d) {
				select(this).selectAll('circle').transition().duration(150)
					.attr('r', (_, i) => nodeRadius(d) + (i === 0 ? 8 : 4));
				// Dim unconnected
				const connectedIds = new Set([d.id]);
				links.forEach((l: any) => {
					const src = typeof l.source === 'string' ? l.source : l.source.id;
					const tgt = typeof l.target === 'string' ? l.target : l.target.id;
					if (src === d.id) connectedIds.add(tgt);
					if (tgt === d.id) connectedIds.add(src);
				});
				nodeGroup.transition().duration(150)
					.attr('opacity', (n) => connectedIds.has(n.id) ? 1 : 0.15);
				link.transition().duration(150)
					.attr('stroke-opacity', (l: any) => {
						const src = typeof l.source === 'string' ? l.source : l.source.id;
						const tgt = typeof l.target === 'string' ? l.target : l.target.id;
						return (src === d.id || tgt === d.id) ? 0.7 : 0.03;
					});
				g.selectAll<SVGTextElement, GraphNode>('text').transition().duration(150)
					.attr('opacity', (n) => connectedIds.has(n.id) ? 1 : 0.1);
			})
			.on('mouseout', function () {
				nodeGroup.each(function (d) {
					select(this).selectAll('circle').transition().duration(300)
						.attr('r', (_, i) => nodeRadius(d) + (i === 0 ? 3 : 0));
				});
				nodeGroup.transition().duration(300).attr('opacity', 1);
				link.transition().duration(300)
					.attr('stroke-opacity', (d) => 0.15 + (d.weight / maxFamilies) * 0.35);
				g.selectAll('text').transition().duration(300).attr('opacity', 1);
			});

		// Tick
		simulation.on('tick', () => {
			link.attr('d', (d: any) => {
				const dx = d.target.x - d.source.x;
				const dy = d.target.y - d.source.y;
				const dr = Math.sqrt(dx * dx + dy * dy) * 1.5;
				return `M${d.source.x},${d.source.y}A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`;
			});
			nodeGroup.attr('transform', (d) => `translate(${d.x},${d.y})`);
			label.attr('x', (d) => d.x!).attr('y', (d) => d.y!);
			label.selectAll('tspan').attr('x', (_, i, els) => {
				const parent = (els[0] as SVGTSpanElement).parentElement as SVGTextElement | null;
				const d = parent ? select<SVGTextElement, GraphNode>(parent).datum() : null;
				return d?.x ?? 0;
			});
		});

		function nodeRadius(d: GraphNode): number {
			if (d.isCenter) return 28;
			return Math.max(8, 8 + (d.families / maxFamilies) * 22);
		}
	}

	function truncate(s: string, max: number): string {
		return s.length > max ? s.slice(0, max - 1) + '…' : s;
	}

	// Auto-search if name provided via URL
	$effect(() => {
		if (initialName) search();
	});
</script>

<svelte:head>
	<title>Co-Applicant Network | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-2xl">Co-Applicant Network</Card.Title>
			<Card.Description>
				Discover who files patents together. Enter an applicant name to see their co-filing partners.
				{#if ctx.names.length > 0}
					<div class="mt-2"><ConsolidatedNames {ctx} /></div>
				{/if}
			</Card.Description>
			<details class="mt-2 text-xs text-muted-foreground">
				<summary class="cursor-pointer hover:text-foreground transition-colors">What am I looking at?</summary>
				<p class="mt-1.5 leading-relaxed">
					Each circle represents an applicant. The <strong>center</strong> is your searched applicant.
					Surrounding circles are co-applicants who filed patents together. <strong>Larger circles</strong>
					= more shared patent families. <strong>Line thickness</strong> = strength of collaboration.
					Colors indicate the co-applicant's country. Drag nodes to rearrange, scroll to zoom.
				</p>
			</details>
		</Card.Header>
		<Card.Content>
			<form onsubmit={(e) => { e.preventDefault(); search(); }} class="flex gap-3">
				<label class="sr-only" for="network-query">Applicant name</label>
				<input
					id="network-query"
					type="text"
					bind:value={query}
					placeholder="e.g. Siemens Aktiengesellschaft"
					class="flex-1 rounded-md border border-input bg-background px-4 py-2 text-sm
						   focus:border-ring focus:ring-2 focus:ring-ring/20 focus:outline-none"
				/>
				<Button type="submit" disabled={loading || !query.trim()}>
					{loading ? 'Loading...' : 'Show Network'}
				</Button>
			</form>
		</Card.Content>
	</Card.Root>

	{#if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">{errorMsg}</div>
	{/if}

	{#if coApplicants.length > 0}
		<!-- Network Graph -->
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<Card.Title>{resolvedName}</Card.Title>
				<Card.Description>{coApplicants.length} co-applicants &middot; {elapsed}ms &middot; drag to rearrange, scroll to zoom</Card.Description>
			</Card.Header>
			<Card.Content class="p-0">
				<svg
					bind:this={svgEl}
					class="w-full rounded-b-lg"
					style="height: 700px;"
					role="img"
					aria-label="Co-applicant network graph for {query}"
				></svg>
			</Card.Content>
		</Card.Root>

		<!-- Table -->
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<Card.Title>Co-Applicant Table</Card.Title>
				<Button variant="outline" size="sm" onclick={() => downloadCsv(coApplicants, `${query.trim()}_co_applicants.csv`)}>
					Export CSV
				</Button>
			</Card.Header>
			<Card.Content class="p-0">
				<Table.Root>
					<Table.Header>
						<Table.Row>
							<Table.Head>Co-Applicant</Table.Head>
							<Table.Head>Country</Table.Head>
							<Table.Head class="text-right">Shared Families</Table.Head>
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each coApplicants as row}
							<Table.Row>
								<Table.Cell>
									<a
										href="{base}/applicant?name={encodeURIComponent(row.co_applicant)}&country={encodeURIComponent(row.country)}"
										class="font-medium hover:underline"
									>
										{row.co_applicant}
									</a>
								</Table.Cell>
								<Table.Cell><Badge variant="outline">{row.country}</Badge></Table.Cell>
								<Table.Cell class="text-right tabular-nums font-medium">
									{row.shared_families.toLocaleString()}
								</Table.Cell>
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</Card.Content>
		</Card.Root>
	{/if}
</div>
