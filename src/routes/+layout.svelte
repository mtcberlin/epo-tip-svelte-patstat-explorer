<script lang="ts">
	import '../app.css';
	import { base } from '$app/paths';
	import { page } from '$app/state';

	let { children } = $props();

	const nav = [
		{ href: '/search', label: 'Applicants' },
		{ href: '/text-search', label: 'Text Search' },
		{ href: '/technology', label: 'Technology' },
		{ href: '/countries', label: 'Countries' },
		{ href: '/query', label: 'AI Query' },
	];

	function isActive(href: string) {
		const path = page.url.pathname;
		return path.startsWith(href);
	}
</script>

<div class="min-h-screen bg-background text-foreground">
	<header class="bg-[var(--mtc-navy)] text-white shadow-md">
		<nav class="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
			<a href="{base}/" class="flex items-center gap-3 transition-opacity hover:opacity-90">
				<img src="{base}/logo.svg" alt="" class="h-8 w-8" />
				<span class="text-lg font-bold tracking-tight">PATSTAT Explorer</span>
			</a>
			<ul class="flex gap-1 text-sm font-medium">
				{#each nav as item}
					<li>
						<a
							href="{base}{item.href}"
							class="rounded-md px-3 py-2 transition-colors
								{isActive(item.href) ? 'bg-white/15 text-white' : 'text-white/70 hover:text-white hover:bg-white/10'}"
						>
							{item.label}
						</a>
					</li>
				{/each}
			</ul>
		</nav>
	</header>

	<main class="mx-auto max-w-7xl px-6 py-8">
		{@render children()}
	</main>

	<footer class="border-t py-6 text-center text-xs text-muted-foreground">
		PATSTAT Explorer &mdash; mtc.berlin &middot; EPO TIP
	</footer>
</div>
