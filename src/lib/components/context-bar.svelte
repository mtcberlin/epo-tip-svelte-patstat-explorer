<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { contextToParams, parseContext } from '$lib/context';
	import { getActiveContext, setActiveContext, clearActiveContext } from '$lib/active-context';
	import X from '@lucide/svelte/icons/x';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';

	import type { AnalysisContext } from '$lib/context';

	// Reactive context: prefer URL params, fallback to stored context
	let storedCtx = $state<AnalysisContext | null>(null);

	// Sync: when URL has context, store it. When URL has no context, use stored.
	$effect(() => {
		const urlCtx = parseContext(page.url.searchParams);
		if (urlCtx.names.length > 0) {
			setActiveContext(urlCtx);
			storedCtx = urlCtx;
		} else {
			storedCtx = getActiveContext();
		}
	});

	const ctx = $derived(storedCtx);
	const hasContext = $derived(ctx !== null && ctx.names.length > 0);
	const ctxParams = $derived(ctx ? contextToParams(ctx) : '');
	const isConsolidated = $derived(ctx ? ctx.names.length > 1 : false);

	// Pages where the applicant submenu makes no sense — they don't use applicant context.
	const STANDALONE_ROUTES = ['/countries', '/query'];
	const isStandalone = $derived(STANDALONE_ROUTES.includes(page.route.id ?? ''));

	let namesExpanded = $state(false);

	function clear() {
		clearActiveContext();
		storedCtx = null;
		namesExpanded = false;
	}

	// Quick links with context
	const links = [
		{ href: '/applicant', label: 'Overview' },
		{ href: '/network', label: 'Network' },
		{ href: '/citations', label: 'Citations' },
		{ href: '/co-occurrence', label: 'CPC Map' },
	] as const;

	function isLinkActive(href: string) {
		return page.route.id === href;
	}
</script>

{#if hasContext && ctx && !isStandalone}
	<div class="bg-[var(--epo-red)]/[0.12] border-b">
		<div class="mx-auto max-w-7xl px-6 py-2 flex items-center gap-4 text-sm">
			<!-- Applicant label + names -->
			<div class="flex items-center gap-2 shrink-0">
				<span class="text-xs text-muted-foreground font-medium uppercase tracking-wider">Analysing</span>
				<button
					class="flex items-center gap-1 font-semibold text-[var(--epo-red)] hover:text-[var(--epo-red)]/80 transition-colors"
					onclick={() => { if (isConsolidated) namesExpanded = !namesExpanded; }}
				>
					{ctx.label}
					{#if isConsolidated}
						<Badge variant="secondary" class="text-xs ml-0.5">{ctx.names.length}</Badge>
						<ChevronDown class="size-3.5 transition-transform {namesExpanded ? 'rotate-180' : ''}" />
					{/if}
				</button>
			</div>

			<!-- Quick nav links -->
			<nav class="flex items-center gap-1 overflow-x-auto no-scrollbar" aria-label="Analysis views">
				{#each links as link}
					<a
						href="{base}{link.href}?{ctxParams}"
						class="rounded-md px-2.5 py-1 text-xs font-medium transition-colors whitespace-nowrap
							{isLinkActive(link.href)
								? 'bg-[var(--epo-red)] text-white'
								: 'text-muted-foreground hover:text-foreground hover:bg-muted'}"
					>
						{link.label}
					</a>
				{/each}
			</nav>

			<!-- Spacer + clear -->
			<div class="ml-auto shrink-0">
				<Button variant="ghost" size="icon-xs" onclick={clear} class="text-muted-foreground hover:text-foreground">
					<X class="size-3.5" />
					<span class="sr-only">Clear analysis context</span>
				</Button>
			</div>
		</div>

		<!-- Expanded names -->
		{#if namesExpanded && isConsolidated}
			<div class="mx-auto max-w-7xl px-6 pb-2">
				<div class="flex flex-wrap gap-1.5">
					{#each ctx.names as name}
						<Badge variant="outline" class="text-xs font-normal">{name}</Badge>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
