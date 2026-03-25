<script lang="ts">
	import { base } from '$app/paths';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Loader from '@lucide/svelte/icons/loader';

	interface PatentDetail {
		appln_id: number;
		appln_auth: string;
		appln_nr: string;
		appln_kind: string;
		appln_filing_date: string;
		appln_filing_year: number;
		docdb_family_id: number;
		granted: number;
		title: string | null;
		title_lang: string | null;
		abstract: string | null;
		applicants: { person_name: string; person_ctry_code: string }[];
		cpc_codes: string[];
	}

	let {
		open = $bindable(false),
		applnId = $bindable<number | null>(null),
	}: {
		open?: boolean;
		applnId?: number | null;
	} = $props();

	let patent = $state<PatentDetail | null>(null);
	let loading = $state(false);
	let errorMsg = $state('');

	async function loadPatent(id: number) {
		loading = true;
		errorMsg = '';
		patent = null;
		try {
			const res = await fetch(`${base}/api/patent/${id}`);
			if (!res.ok) {
				const text = await res.text();
				throw new Error(text || `Status ${res.status}`);
			}
			patent = await res.json();
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (open && applnId) {
			loadPatent(applnId);
		}
		if (!open) {
			patent = null;
			errorMsg = '';
		}
	});

	function espacenetUrl(auth: string, nr: string): string {
		return `https://worldwide.espacenet.com/patent/search?q=pn%3D${auth}${nr}`;
	}

	function cpcExplorerUrl(cpc: string): string {
		const slug = cpc.toLowerCase().replace(/[\s/]+/g, '-');
		return `https://patentclassificationexplorer.com/cpc/${slug}`;
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="sm:max-w-lg overflow-y-auto">
		<Sheet.Header class="pr-8">
			<Sheet.Title>Patent Details</Sheet.Title>
			{#if patent}
				<Sheet.Description>{patent.appln_auth}{patent.appln_nr}</Sheet.Description>
			{/if}
		</Sheet.Header>

		<div class="px-4 pb-6 space-y-5">
			{#if loading}
				<div class="flex items-center justify-center py-12 text-muted-foreground">
					<Loader class="size-5 animate-spin mr-2" />
					Loading...
				</div>
			{:else if errorMsg}
				<div class="rounded-lg bg-destructive/10 p-4 text-sm text-destructive" role="alert">
					{errorMsg}
				</div>
			{:else if patent}
				<!-- Title -->
				{#if patent.title}
					<div>
						<h3 class="text-sm font-semibold leading-snug">{patent.title}</h3>
					</div>
				{/if}

				<!-- Basic Info -->
				<Card.Root size="sm">
					<Card.Content class="pt-3">
						<dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
							<dt class="text-muted-foreground">Application ID</dt>
							<dd class="font-mono">{patent.appln_id}</dd>

							<dt class="text-muted-foreground">Authority</dt>
							<dd><Badge variant="outline">{patent.appln_auth}</Badge></dd>

							<dt class="text-muted-foreground">Filing Date</dt>
							<dd>{patent.appln_filing_date}</dd>

							<dt class="text-muted-foreground">Kind</dt>
							<dd>{patent.appln_kind}</dd>

							<dt class="text-muted-foreground">DOCDB Family</dt>
							<dd class="font-mono">{patent.docdb_family_id}</dd>

							<dt class="text-muted-foreground">Granted</dt>
							<dd>{patent.granted ? 'Yes' : 'No'}</dd>
						</dl>
					</Card.Content>
				</Card.Root>

				<!-- Abstract -->
				{#if patent.abstract}
					<div>
						<h4 class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">Abstract</h4>
						<p class="text-sm leading-relaxed">{patent.abstract}</p>
					</div>
				{/if}

				<Separator />

				<!-- Applicants -->
				<div>
					<h4 class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Applicants</h4>
					{#if patent.applicants.length > 0}
						<div class="space-y-1.5">
							{#each patent.applicants as applicant}
								<div class="flex items-center gap-2 text-sm">
									<a
										href="{base}/applicant?name={encodeURIComponent(applicant.person_name)}"
										class="text-[var(--mtc-blue)] hover:underline"
									>
										{applicant.person_name}
									</a>
									{#if applicant.person_ctry_code}
										<Badge variant="secondary" class="text-xs">{applicant.person_ctry_code}</Badge>
									{/if}
								</div>
							{/each}
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No applicants linked.</p>
					{/if}
				</div>

				<Separator />

				<!-- CPC Codes -->
				<div>
					<h4 class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">CPC Classifications</h4>
					{#if patent.cpc_codes.length > 0}
						<div class="flex flex-wrap gap-1.5">
							{#each patent.cpc_codes as cpc}
								<Badge variant="outline" href={cpcExplorerUrl(cpc)} class="font-mono text-xs">
									{cpc}
								</Badge>
							{/each}
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No CPC codes linked.</p>
					{/if}
				</div>

				<Separator />

				<!-- External Link -->
				<Button
					variant="outline"
					href={espacenetUrl(patent.appln_auth, patent.appln_nr)}
					class="w-full"
				>
					<ExternalLink class="size-4" />
					View on Espacenet
				</Button>
			{/if}
		</div>
	</Sheet.Content>
</Sheet.Root>
