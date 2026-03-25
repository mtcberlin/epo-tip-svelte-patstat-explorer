<script lang="ts">
	import { base } from '$app/paths';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';

	let status = $state<{ ok: boolean; message: string } | null>(null);
	let loading = $state(false);

	async function checkConnection() {
		loading = true;
		try {
			const res = await fetch(`${base}/api/health`);
			status = await res.json();
		} catch (e) {
			status = { ok: false, message: `Connection failed: ${e}` };
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-8">
	<Card.Root>
		<Card.Header>
			<div class="flex items-center gap-4">
				<img src="{base}/logo.png" alt="" class="h-14 w-14" />
				<div>
					<Card.Title class="text-3xl">PATSTAT Explorer</Card.Title>
					<Card.Description>mtc.berlin &middot; EPO TIP</Card.Description>
				</div>
			</div>
		</Card.Header>
		<Card.Content class="space-y-4">
			<p class="text-muted-foreground">
				Search and analyse patent data from PATSTAT via BigQuery &mdash;
				applicant trends, co-filing networks, citation flows, technology classifications.
			</p>

			<div class="flex flex-wrap gap-3">
				<Button href="{base}/search" size="lg">
					Start with Applicant Search
				</Button>
				<Button href="{base}/query" variant="outline">
					AI Query
				</Button>
				<Button href="{base}/text-search" variant="outline">
					Text Search
				</Button>
				<Button href="{base}/technology" variant="outline">
					Technology Fields
				</Button>
				<Button href="{base}/countries" variant="outline">
					Country Comparison
				</Button>
			</div>
		</Card.Content>
	</Card.Root>

	<Card.Root>
		<Card.Header>
			<Card.Title class="text-base">How it works</Card.Title>
		</Card.Header>
		<Card.Content>
			<div class="grid gap-4 sm:grid-cols-4 text-sm">
				<div>
					<div class="font-semibold text-[var(--mtc-navy)]">1. Search</div>
					<p class="text-muted-foreground mt-1">Find applicants by name, keywords, or CPC codes.</p>
				</div>
				<div>
					<div class="font-semibold text-[var(--mtc-navy)]">2. Consolidate</div>
					<p class="text-muted-foreground mt-1">Merge name variants into a single entity.</p>
				</div>
				<div>
					<div class="font-semibold text-[var(--mtc-navy)]">3. Analyse</div>
					<p class="text-muted-foreground mt-1">Filing trends, jurisdictions, technology fields.</p>
				</div>
				<div>
					<div class="font-semibold text-[var(--mtc-navy)]">4. Deep Dive</div>
					<p class="text-muted-foreground mt-1">Co-filing networks, citation flows, patent texts.</p>
				</div>
			</div>
		</Card.Content>
	</Card.Root>

	<div class="flex items-center gap-3">
		<Button onclick={checkConnection} disabled={loading} variant="ghost" size="sm">
			{loading ? 'Checking...' : 'Check PATSTAT Connection'}
		</Button>
		{#if status}
			<span class="text-xs {status.ok ? 'text-green-600' : 'text-destructive'}">
				{status.ok ? 'Connected' : 'Error'} &mdash; {status.message}
			</span>
		{/if}
	</div>
</div>
