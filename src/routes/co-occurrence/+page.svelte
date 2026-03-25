<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { downloadCsv } from '$lib/csv';
	import { parseContext, nameWhereClause } from '$lib/context';
	import ConsolidatedNames from '$lib/components/consolidated-names.svelte';

	const ctx = $derived(parseContext(page.url.searchParams));
	const hasContext = $derived(ctx.names.length > 0);

	const CPC_SECTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'Y'] as const;
	const SECTION_LABELS: Record<string, string> = {
		A: 'Human necessities',
		B: 'Operations; Transport',
		C: 'Chemistry; Metallurgy',
		D: 'Textiles; Paper',
		E: 'Fixed constructions',
		F: 'Mech. engineering',
		G: 'Physics',
		H: 'Electricity',
		Y: 'Emerging tech',
	};

	interface CoOccurrenceEntry {
		section1: string;
		section2: string;
		family_count: number;
	}

	interface Cell {
		row: string;
		col: string;
		count: number;
	}

	let rawData = $state<CoOccurrenceEntry[]>([]);
	let loading = $state(false);
	let errorMsg = $state('');
	let elapsed = $state(0);

	function buildMatrix(data: CoOccurrenceEntry[]): Cell[] {
		const lookup = new Map<string, number>();
		for (const d of data) {
			lookup.set(`${d.section1}-${d.section2}`, d.family_count);
			lookup.set(`${d.section2}-${d.section1}`, d.family_count);
		}
		const cells: Cell[] = [];
		for (const row of CPC_SECTIONS) {
			for (const col of CPC_SECTIONS) {
				cells.push({ row, col, count: lookup.get(`${row}-${col}`) ?? 0 });
			}
		}
		return cells;
	}

	const matrix = $derived(buildMatrix(rawData));
	const maxCount = $derived(Math.max(1, ...matrix.map((c) => c.count)));

	function cellColor(count: number): string {
		if (count === 0) return 'var(--muted)';
		const intensity = Math.pow(count / maxCount, 0.5); // sqrt scale for better visual range
		// Interpolate from light blue to mtc-navy
		const l = 90 - intensity * 60; // lightness: 90% → 30%
		const c = intensity * 0.15;    // chroma: 0 → 0.15
		return `oklch(${l}% ${c} 260)`;
	}

	function cellTitle(row: string, col: string, count: number): string {
		return `${SECTION_LABELS[row]} × ${SECTION_LABELS[col]}: ${count} families`;
	}

	async function loadCoOccurrence() {
		if (!hasContext) return;

		loading = true;
		errorMsg = '';
		rawData = [];
		const t0 = performance.now();

		const where = `pa.applt_seq_nr > 0 AND ${nameWhereClause(ctx)}`;

		try {
			const res = await fetch(`${base}/api/co-occurrence`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ where_clause: where })
			});
			if (!res.ok) throw new Error(await res.text());
			rawData = await res.json();
			elapsed = Math.round(performance.now() - t0);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (hasContext) loadCoOccurrence();
	});

	// SVG sizing
	const cellSize = 56;
	const labelWidth = 24;
	const svgWidth = labelWidth + CPC_SECTIONS.length * cellSize;
	const svgHeight = labelWidth + CPC_SECTIONS.length * cellSize;

	// Hover state
	let hoveredCell = $state<Cell | null>(null);
</script>

<svelte:head>
	<title>CPC Co-Occurrence | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-2xl">CPC Co-Occurrence Heatmap</Card.Title>
			<Card.Description>
				Shows how often two CPC sections appear together on the same patent family.
				{#if hasContext}
					<div class="mt-2"><ConsolidatedNames {ctx} /></div>
				{:else}
					<br/>Navigate here from an applicant or technology view to see co-occurrences.
				{/if}
			</Card.Description>
		</Card.Header>
	</Card.Root>

	{#if !hasContext}
		<Card.Root>
			<Card.Content class="py-12 text-center text-muted-foreground">
				<p>Select an applicant first to generate the co-occurrence matrix.</p>
				<Button href="{base}/search" variant="outline" class="mt-4">
					Go to Applicant Search
				</Button>
			</Card.Content>
		</Card.Root>
	{:else if loading}
		<Card.Root>
			<Card.Content class="py-12 text-center text-muted-foreground">
				Loading co-occurrence data...
			</Card.Content>
		</Card.Root>
	{:else if errorMsg}
		<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">{errorMsg}</div>
	{:else if rawData.length > 0}
		<Card.Root>
			<Card.Header class="flex-row items-center justify-between">
				<div>
					<Card.Title>Co-Occurrence Matrix</Card.Title>
					<Card.Description>
						{rawData.length} pairs &middot; {elapsed}ms
					</Card.Description>
				</div>
				<Button variant="outline" size="sm" onclick={() => {
					const exportData = rawData.map(d => ({
						section1: d.section1,
						section1_label: SECTION_LABELS[d.section1] ?? d.section1,
						section2: d.section2,
						section2_label: SECTION_LABELS[d.section2] ?? d.section2,
						family_count: d.family_count,
					}));
					downloadCsv(exportData, `co_occurrence_${ctx.label.replace(/\s+/g, '_')}.csv`);
				}}>
					Export CSV
				</Button>
			</Card.Header>
			<Card.Content>
				<!-- Tooltip -->
				{#if hoveredCell && hoveredCell.count > 0}
					<div class="mb-3 text-sm">
						<span class="font-semibold">{hoveredCell.row}</span> ({SECTION_LABELS[hoveredCell.row]})
						&times;
						<span class="font-semibold">{hoveredCell.col}</span> ({SECTION_LABELS[hoveredCell.col]}):
						<span class="font-bold text-[var(--mtc-blue)]">{hoveredCell.count}</span> families
					</div>
				{:else}
					<div class="mb-3 text-sm text-muted-foreground">Hover over a cell to see details</div>
				{/if}

				<!-- Heatmap SVG -->
				<div class="overflow-x-auto">
					<svg
						width={svgWidth}
						height={svgHeight}
						viewBox="0 0 {svgWidth} {svgHeight}"
						class="mx-auto"
						role="img"
						aria-label="CPC section co-occurrence heatmap"
					>
						<!-- Column labels (top) -->
						{#each CPC_SECTIONS as section, i}
							<text
								x={labelWidth + i * cellSize + cellSize / 2}
								y={16}
								text-anchor="middle"
								class="fill-foreground text-xs font-semibold"
							>{section}</text>
						{/each}

						<!-- Row labels (left) + cells -->
						{#each CPC_SECTIONS as rowSection, ri}
							<text
								x={14}
								y={labelWidth + ri * cellSize + cellSize / 2 + 4}
								text-anchor="middle"
								class="fill-foreground text-xs font-semibold"
							>{rowSection}</text>

							{#each CPC_SECTIONS as colSection, ci}
								{@const cell = matrix[ri * CPC_SECTIONS.length + ci]}
								<rect
									x={labelWidth + ci * cellSize + 1}
									y={labelWidth + ri * cellSize + 1}
									width={cellSize - 2}
									height={cellSize - 2}
									rx="4"
									fill={cellColor(cell.count)}
									class="transition-opacity"
									opacity={hoveredCell && hoveredCell !== cell ? 0.6 : 1}
									onmouseenter={() => (hoveredCell = cell)}
									onmouseleave={() => (hoveredCell = null)}
									role="gridcell"
									aria-label={cellTitle(rowSection, colSection, cell.count)}
								>
									<title>{cellTitle(rowSection, colSection, cell.count)}</title>
								</rect>
								{#if cell.count > 0}
									<text
										x={labelWidth + ci * cellSize + cellSize / 2}
										y={labelWidth + ri * cellSize + cellSize / 2 + 4}
										text-anchor="middle"
										class="text-[10px] font-medium pointer-events-none"
										fill={cell.count / maxCount > 0.4 ? 'white' : 'var(--foreground)'}
									>{cell.count}</text>
								{/if}
							{/each}
						{/each}
					</svg>
				</div>

				<!-- Legend -->
				<div class="flex items-center gap-2 mt-4 text-xs text-muted-foreground justify-center">
					<span>0</span>
					<div class="flex h-3 rounded overflow-hidden">
						{#each Array(10) as _, i}
							<div
								class="w-4"
								style="background: {cellColor(((i + 1) / 10) * maxCount)}"
							></div>
						{/each}
					</div>
					<span>{maxCount}</span>
					<span class="ml-1">families</span>
				</div>
			</Card.Content>
		</Card.Root>
	{:else}
		<Card.Root>
			<Card.Content class="py-8 text-center text-muted-foreground">
				No CPC co-occurrences found for this applicant.
			</Card.Content>
		</Card.Root>
	{/if}
</div>
