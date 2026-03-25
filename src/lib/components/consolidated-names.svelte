<script lang="ts">
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Badge } from '$lib/components/ui/badge';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';

	import type { AnalysisContext } from '$lib/context';

	let { ctx }: { ctx: AnalysisContext } = $props();

	const isConsolidated = $derived(ctx.names.length > 1);
	let open = $state(false);
</script>

{#if isConsolidated}
	<Collapsible.Root bind:open>
		<Collapsible.Trigger class="inline-flex items-center gap-1.5 text-sm">
			<Badge variant="secondary">{ctx.label}</Badge>
			<span class="text-xs text-muted-foreground">{ctx.names.length} names</span>
			{#if open}
				<ChevronDown class="size-3.5 text-muted-foreground" />
			{:else}
				<ChevronRight class="size-3.5 text-muted-foreground" />
			{/if}
		</Collapsible.Trigger>
		<Collapsible.Content>
			<div class="mt-2 flex flex-wrap gap-1.5">
				{#each ctx.names as name}
					<Badge variant="outline" class="text-xs font-normal">{name}</Badge>
				{/each}
			</div>
		</Collapsible.Content>
	</Collapsible.Root>
{:else if ctx.names.length === 1}
	<Badge variant="outline">{ctx.label}</Badge>
{/if}
