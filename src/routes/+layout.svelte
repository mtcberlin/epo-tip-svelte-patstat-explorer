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

	<footer class="border-t bg-muted/30">
		<div class="mx-auto max-w-7xl px-6 py-10">
			<div class="grid gap-8 sm:grid-cols-3">
				<!-- Brand -->
				<div>
					<div class="flex items-center gap-2 mb-3">
						<img src="{base}/logo.svg" alt="" class="h-6 w-6" />
						<span class="font-bold text-sm text-foreground">PATSTAT Explorer</span>
					</div>
					<p class="text-xs text-muted-foreground leading-relaxed">
						Patent analysis &amp; visualization on EPO PATSTAT Global via BigQuery.
					</p>
					<p class="text-xs text-muted-foreground mt-2">
						Data: EPO PATSTAT Global
					</p>
				</div>

				<!-- Links -->
				<div>
					<h4 class="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Links</h4>
					<ul class="space-y-1.5 text-xs">
						<li><a href="{base}/about" class="text-muted-foreground hover:text-foreground transition-colors">About this app</a></li>
						<li><a href="https://mtc.berlin" target="_blank" rel="noopener" class="text-muted-foreground hover:text-foreground transition-colors">mtc.berlin</a></li>
						<li><a href="https://depa.tech" target="_blank" rel="noopener" class="text-muted-foreground hover:text-foreground transition-colors">depa.tech</a></li>
						<li><a href="https://patentreports.depa.tech" target="_blank" rel="noopener" class="text-muted-foreground hover:text-foreground transition-colors">Patent Intelligence Reports</a></li>
					</ul>
				</div>

				<!-- Contact -->
				<div>
					<h4 class="text-xs font-semibold text-foreground uppercase tracking-wider mb-3">Contact</h4>
					<ul class="space-y-1.5 text-xs">
						<li>
							<a href="https://www.linkedin.com/in/arne-krueger/" target="_blank" rel="noopener"
								class="text-muted-foreground hover:text-foreground transition-colors">
								Arne Krueger &mdash; LinkedIn
							</a>
						</li>
						<li>
							<a href="https://calendly.com/arne-krueger-mtc" target="_blank" rel="noopener"
								class="text-muted-foreground hover:text-foreground transition-colors">
								Book a call
							</a>
						</li>
					</ul>
				</div>
			</div>

			<div class="mt-8 pt-6 border-t text-center text-xs text-muted-foreground">
				&copy; {new Date().getFullYear()} <a href="https://mtc.berlin" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">mtc.berlin</a>
			</div>
		</div>
	</footer>
</div>
