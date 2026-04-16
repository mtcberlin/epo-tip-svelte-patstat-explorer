<script lang="ts">
	import { base } from '$app/paths';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import Search from '@lucide/svelte/icons/search';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Globe from '@lucide/svelte/icons/globe';
	import Cpu from '@lucide/svelte/icons/cpu';

	let status = $state<{ ok: boolean; message: string } | null>(null);

	// Auto-check connection on load
	$effect(() => {
		fetch(`${base}/api/health`)
			.then((r) => r.json())
			.then((d) => (status = d))
			.catch(() => (status = { ok: false, message: 'Connection failed' }));
	});
</script>

<svelte:head>
	<title>TIP4PATLIBs PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-10">
	<!-- Hero -->
	<div class="space-y-3 pt-4">
		<div class="flex items-center justify-between gap-4">
			<h2 class="text-4xl font-bold text-[var(--epo-dark)]">TIP4PATLIBs PATSTAT Explorer</h2>
			<div class="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
				{#if status}
					<span class="inline-block h-2 w-2 rounded-full {status.ok ? 'bg-green-500' : 'bg-destructive'}"></span>
					<span>{status.ok ? 'PATSTAT connected' : 'Connection error'}</span>
				{:else}
					<span class="inline-block h-2 w-2 rounded-full bg-muted animate-pulse"></span>
					<span>Checking connection...</span>
				{/if}
			</div>
		</div>
		<p class="text-muted-foreground max-w-3xl leading-relaxed">
			Search and analyse patent data in the EPO Technology Intelligence Platform - applicant name harmonisation, co-filing networks, citation flows and technology classifications in an easy to use Web Application.
		</p>
	</div>

	<!-- How it works (informational, no card chrome — non-card content = "read me") -->
	<div class="space-y-3">
		<h3 class="text-sm font-semibold text-muted-foreground uppercase tracking-wider">How it works</h3>
		<div class="grid gap-6 sm:grid-cols-3 text-sm">
			<div class="space-y-1.5">
				<div class="font-semibold text-[var(--epo-dark)]">1. Search</div>
				<p class="text-muted-foreground">Find applicants or technologies.</p>
			</div>
			<div class="space-y-1.5">
				<div class="font-semibold text-[var(--epo-dark)]">2. Consolidate</div>
				<p class="text-muted-foreground">Group name variants of the same organisation.</p>
			</div>
			<div class="space-y-1.5">
				<div class="font-semibold text-[var(--epo-dark)]">3. Analyse</div>
				<p class="text-muted-foreground">Get an overview, co-filing network, citation map, CPC map.</p>
			</div>
		</div>
	</div>

	<!-- Primary entry points: connected pair that lead into the deep-dive -->
	<div class="grid gap-4 sm:grid-cols-2">
		<a href="{base}/search" class="group">
			<Card.Root class="h-full bg-muted/30 transition-colors group-hover:border-[var(--mtc-blue)]/40">
				<Card.Content class="pt-5 space-y-2">
					<div class="flex items-center gap-2">
						<Search class="size-5 text-[var(--epo-dark)]" />
						<span class="font-semibold">Applicant Search</span>
					</div>
					<p class="text-sm text-muted-foreground leading-relaxed">
						Find applicants by name. Group name variants (Siemens AG, Siemens Ltd, ...) and analyse filing trends, jurisdictions, and technology fields.
					</p>
				</Card.Content>
			</Card.Root>
		</a>
		<a href="{base}/technology" class="group">
			<Card.Root class="h-full bg-muted/30 transition-colors group-hover:border-[var(--mtc-blue)]/40">
				<Card.Content class="pt-5 space-y-2">
					<div class="flex items-center gap-2">
						<Cpu class="size-5 text-[var(--epo-dark)]" />
						<span class="font-semibold">Technology Search</span>
					</div>
					<p class="text-sm text-muted-foreground leading-relaxed">
						Search by CPC classification code. Find the top applicants in any technology area, then click through into the same deep-dive analysis.
					</p>
				</Card.Content>
			</Card.Root>
		</a>
	</div>

	<!-- Secondary entry points: standalone tools -->
	<div class="space-y-3">
		<h3 class="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Other tools</h3>
		<div class="grid gap-4 sm:grid-cols-2">
			<a href="{base}/countries" class="group">
				<Card.Root class="h-full bg-muted/30 transition-colors group-hover:border-[var(--mtc-blue)]/40">
					<Card.Content class="pt-5 space-y-2">
						<div class="flex items-center gap-2">
							<Globe class="size-5 text-[var(--epo-dark)]" />
							<span class="font-semibold">Country Comparison</span>
						</div>
						<p class="text-sm text-muted-foreground leading-relaxed">
							Compare patent filing trends across countries. Filter by technology field to see who leads where.
						</p>
					</Card.Content>
				</Card.Root>
			</a>
			<a href="{base}/query" class="group">
				<Card.Root class="h-full bg-muted/30 transition-colors group-hover:border-[var(--mtc-blue)]/40">
					<Card.Content class="pt-5 space-y-2">
						<div class="flex items-center gap-2">
							<Sparkles class="size-5 text-[var(--epo-dark)]" />
							<span class="font-semibold">AI Query</span>
							<Badge variant="secondary" class="text-xs">MCP</Badge>
						</div>
						<p class="text-sm text-muted-foreground leading-relaxed">
							Ask questions in natural language. Claude explores the PATSTAT schema via MCP and builds SQL for you - step by step.
						</p>
					</Card.Content>
				</Card.Root>
			</a>
		</div>
	</div>
</div>
