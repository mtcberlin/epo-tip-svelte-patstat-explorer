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
	<title>PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-10">
	<!-- Hero -->
	<div class="text-center space-y-4 pt-4">
		<div class="flex items-center justify-center gap-3">
			<img src="{base}/logo.png" alt="" class="h-12 w-12" />
			<h1 class="text-4xl font-bold text-[var(--mtc-navy)]">PATSTAT Explorer</h1>
		</div>
		<p class="text-muted-foreground max-w-lg mx-auto leading-relaxed">
			Search and analyse patent data from the EPO PATSTAT database -
			applicant trends, co-filing networks, citation flows, and technology classifications.
		</p>
		<div class="flex items-center justify-center gap-2 text-xs text-muted-foreground">
			{#if status}
				<span class="inline-block h-2 w-2 rounded-full {status.ok ? 'bg-green-500' : 'bg-destructive'}"></span>
				<span>{status.ok ? 'PATSTAT connected' : 'Connection error'}</span>
			{:else}
				<span class="inline-block h-2 w-2 rounded-full bg-muted animate-pulse"></span>
				<span>Checking connection...</span>
			{/if}
		</div>
	</div>

	<!-- Main entry points -->
	<div class="grid gap-4 sm:grid-cols-2">
		<a href="{base}/search" class="group">
			<Card.Root class="h-full transition-colors group-hover:border-[var(--mtc-blue)]/40">
				<Card.Content class="pt-5 space-y-2">
					<div class="flex items-center gap-2">
						<Search class="size-5 text-[var(--mtc-blue)]" />
						<span class="font-semibold">Applicant Search</span>
					</div>
					<p class="text-sm text-muted-foreground leading-relaxed">
						Find applicants by name. Group name variants (Siemens AG, Siemens Ltd, ...) and analyse filing trends, jurisdictions, and technology fields.
					</p>
				</Card.Content>
			</Card.Root>
		</a>
		<a href="{base}/query" class="group">
			<Card.Root class="h-full transition-colors group-hover:border-[var(--mtc-blue)]/40">
				<Card.Content class="pt-5 space-y-2">
					<div class="flex items-center gap-2">
						<Sparkles class="size-5 text-[var(--mtc-blue)]" />
						<span class="font-semibold">AI Query</span>
						<Badge variant="secondary" class="text-xs">MCP</Badge>
					</div>
					<p class="text-sm text-muted-foreground leading-relaxed">
						Ask questions in natural language. Claude explores the PATSTAT schema via MCP and builds SQL for you - step by step.
					</p>
				</Card.Content>
			</Card.Root>
		</a>
		<a href="{base}/technology" class="group">
			<Card.Root class="h-full transition-colors group-hover:border-[var(--mtc-blue)]/40">
				<Card.Content class="pt-5 space-y-2">
					<div class="flex items-center gap-2">
						<Cpu class="size-5 text-[var(--mtc-blue)]" />
						<span class="font-semibold">Technology Fields</span>
					</div>
					<p class="text-sm text-muted-foreground leading-relaxed">
						Browse by CPC classification code. See filing trends and top applicants for any technology area.
					</p>
				</Card.Content>
			</Card.Root>
		</a>
		<a href="{base}/countries" class="group">
			<Card.Root class="h-full transition-colors group-hover:border-[var(--mtc-blue)]/40">
				<Card.Content class="pt-5 space-y-2">
					<div class="flex items-center gap-2">
						<Globe class="size-5 text-[var(--mtc-blue)]" />
						<span class="font-semibold">Country Comparison</span>
					</div>
					<p class="text-sm text-muted-foreground leading-relaxed">
						Compare patent filing trends across countries. Filter by technology field to see who leads where.
					</p>
				</Card.Content>
			</Card.Root>
		</a>
	</div>

	<!-- How it works -->
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-base">How it works</Card.Title>
		</Card.Header>
		<Card.Content>
			<div class="grid gap-6 sm:grid-cols-4 text-sm">
				<div class="space-y-1.5">
					<div class="font-semibold text-[var(--mtc-navy)]">1. Search</div>
					<p class="text-muted-foreground">Find applicants by name, keywords, or CPC codes.</p>
				</div>
				<div class="space-y-1.5">
					<div class="font-semibold text-[var(--mtc-navy)]">2. Consolidate</div>
					<p class="text-muted-foreground">Group name variants of the same organisation into one entity.</p>
				</div>
				<div class="space-y-1.5">
					<div class="font-semibold text-[var(--mtc-navy)]">3. Analyse</div>
					<p class="text-muted-foreground">Filing trends, jurisdictions, technology fields - all at a glance.</p>
				</div>
				<div class="space-y-1.5">
					<div class="font-semibold text-[var(--mtc-navy)]">4. Deep Dive</div>
					<p class="text-muted-foreground">Co-filing networks, citation flows, patent texts, CPC heatmaps.</p>
				</div>
			</div>
		</Card.Content>
	</Card.Root>

	<!-- Quick examples -->
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-base">Try it</Card.Title>
		</Card.Header>
		<Card.Content>
			<div class="grid gap-2 sm:grid-cols-3 text-sm">
				<a href="{base}/search" class="rounded-lg border p-3 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors">
					Search for <span class="font-medium text-foreground">BASF</span> and consolidate name variants
				</a>
				<a href="{base}/technology" class="rounded-lg border p-3 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors">
					Explore <span class="font-medium text-foreground">H01M</span> (batteries) technology landscape
				</a>
				<a href="{base}/countries" class="rounded-lg border p-3 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors">
					Compare <span class="font-medium text-foreground">DE, US, CN, JP, KR</span> filing trends
				</a>
			</div>
		</Card.Content>
	</Card.Root>
</div>
