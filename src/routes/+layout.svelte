<script lang="ts">
	import '../app.css';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import ContextBar from '$lib/components/context-bar.svelte';

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

	<ContextBar />

	<main class="mx-auto max-w-7xl px-6 py-8">
		{@render children()}
	</main>

	<footer class="border-t bg-muted/30 mt-12">
		<div class="mx-auto max-w-7xl px-6 py-10">
			<!-- Top row: brand left, link groups right -->
			<div class="flex flex-col sm:flex-row gap-10 sm:gap-16">
				<!-- Brand -->
				<div class="sm:max-w-[240px]">
					<div class="flex items-center gap-2.5 mb-3">
						<img src="{base}/logo.svg" alt="" class="h-5 w-5 opacity-60" />
						<span class="font-semibold text-sm text-foreground">PATSTAT Explorer</span>
					</div>
					<p class="text-xs text-muted-foreground leading-relaxed">
						Patent analysis &amp; visualization on EPO PATSTAT Global via BigQuery.
					</p>
				</div>

				<!-- Link groups -->
				<div class="flex gap-16 text-xs">
					<div>
						<h4 class="font-semibold text-foreground mb-3">Product</h4>
						<ul class="space-y-2 text-muted-foreground">
							<li><a href="{base}/about" class="hover:text-foreground transition-colors">About</a></li>
							<li><a href="https://github.com/mtcberlin/epo-tip-svelte-patstat-explorer" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">GitHub</a></li>
							<li><a href="https://patentreports.depa.tech" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Patent Reports</a></li>
						</ul>
					</div>
					<div>
						<h4 class="font-semibold text-foreground mb-3">Company</h4>
						<ul class="space-y-2 text-muted-foreground">
							<li><a href="https://mtc.berlin" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">mtc.berlin</a></li>
							<li><a href="https://depa.tech" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">depa.tech</a></li>
						</ul>
					</div>
					<div>
						<h4 class="font-semibold text-foreground mb-3">Contact</h4>
						<ul class="space-y-2 text-muted-foreground">
							<li><a href="https://www.linkedin.com/in/herrkrueger/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">LinkedIn</a></li>
							<li><a href="https://calendly.com/herrkrueger/patent-intelligence" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Book a call</a></li>
						</ul>
					</div>
				</div>
			</div>

			<!-- Bottom bar -->
			<div class="mt-8 pt-5 border-t flex items-center justify-between text-xs text-muted-foreground">
				<span>&copy; {new Date().getFullYear()} <a href="https://mtc.berlin" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">mtc.berlin</a></span>
				<span>Data: EPO PATSTAT Global</span>
			</div>
		</div>
	</footer>
</div>
