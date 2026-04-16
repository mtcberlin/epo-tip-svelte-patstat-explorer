<script lang="ts">
	import '../app.css';
	import { base } from '$app/paths';
	import ContextBar from '$lib/components/context-bar.svelte';

	let { children } = $props();
</script>

<div class="min-h-screen bg-background text-foreground">
	<header class="bg-[var(--epo-red)] text-white shadow-md">
		<nav class="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
			<a href="{base}/" class="flex items-center gap-3 transition-opacity hover:opacity-90">
				<img src="{base}/logo.svg" alt="" class="h-8 w-8" />
				<h1 class="text-lg font-bold tracking-tight">EPO Academy Training Material</h1>
			</a>
		</nav>
	</header>

	<ContextBar />

	<main class="mx-auto max-w-7xl px-6 py-8">
		{@render children()}
	</main>

	<footer class="border-t bg-muted/30 mt-12">
		<div class="mx-auto max-w-7xl px-6 py-8 flex items-start justify-between gap-8 text-xs text-muted-foreground">
			<div class="space-y-1.5">
				<div>&copy; 2026, All rights reserved</div>
				<div>
					<a href="https://www.epo.org/en/learning" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">EPO Academy</a>
				</div>
				<div>
					<a href="https://mtc.berlin/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">mtc.berlin</a>
					<span class="mx-1">/</span>
					<a href="https://depa.tech/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">depa.tech</a>
				</div>
			</div>
			<div class="space-y-1.5 text-right">
				<div>
					Concept:
					<a href="https://www.linkedin.com/in/herrkrueger/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Arne Krueger</a>
				</div>
				<div>
					Architecture:
					<a href="https://www.linkedin.com/in/matzeschmidbauer/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Matze Schmidbauer</a>
				</div>
				<div>
					Inspiration:
					<a href="https://www.linkedin.com/in/chris-toft-/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Chris Toft</a>
				</div>
			</div>
		</div>
	</footer>
</div>
