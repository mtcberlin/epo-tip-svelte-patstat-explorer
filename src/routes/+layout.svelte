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
				<h1 class="text-lg font-bold tracking-tight">TIP4PATLIBs PATSTAT Explorer</h1>
			</a>
		</nav>
	</header>

	<ContextBar />

	<main class="mx-auto max-w-7xl px-6 py-8">
		{@render children()}
	</main>

	<footer class="border-t bg-muted/30 mt-12">
		<div class="mx-auto max-w-7xl px-6 py-10">
			<div class="grid grid-cols-2 gap-8 sm:grid-cols-5">
				<!-- Brand — spans 2 cols -->
				<div class="col-span-2">
					<div class="flex items-center gap-2.5 mb-3">
						<img src="{base}/logo-dark.svg" alt="" class="h-6 w-6" />
						<span class="font-semibold text-sm text-foreground">TIP4PATLIBs PATSTAT Explorer</span>
					</div>
					<p class="text-xs text-muted-foreground leading-relaxed max-w-[260px]">
						Created for the EPO Academy and PATLIB TIP Working Group in March 2026
					</p>
				</div>

				<!-- EPO Academy -->
				<div class="text-xs">
					<h4 class="font-semibold text-foreground mb-3">EPO Academy</h4>
					<ul class="space-y-2 text-muted-foreground">
						<li><a href="https://e-courses.epo.org/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Online training</a></li>
						<li><a href="https://www.epo.org/learning/training.html" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Training events</a></li>
						<li><a href="https://epo.org/academy-training-catalogue" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Training catalogue</a></li>
					</ul>
				</div>

				<!-- EPO Data -->
				<div class="text-xs">
					<h4 class="font-semibold text-foreground mb-3">EPO Data</h4>
					<ul class="space-y-2 text-muted-foreground">
						<li><a href="https://www.epo.org/en/searching-for-patents/data/technology-intelligence-platform" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Technology Intelligence Platform</a></li>
						<li><a href="https://tip.epo.org/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Open Tip</a></li>
						<li><a href="https://e-courses.epo.org/enrol/index.php?id=416" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">An Introduction to TIP</a></li>
					</ul>
				</div>

				<!-- Contact -->
				<div class="text-xs">
					<h4 class="font-semibold text-foreground mb-3">Contact</h4>
					<ul class="space-y-2 text-muted-foreground">
						<li><a href="https://www.epo.org/en/contact-us?topic=pk&amp;subject_searching_pk=tip" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Contact form</a></li>
						<li><a href="https://www.linkedin.com/company/european-patent-office/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">LinkedIn</a></li>
					</ul>
				</div>
			</div>

			<!-- Bottom bar -->
			<div class="mt-8 pt-5 border-t flex items-center justify-between text-xs text-muted-foreground">
				<span>&copy; 2026, All rights reserved</span>
				<span>
					Author:
					<a href="https://www.linkedin.com/in/herrkrueger/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Arne Krueger</a>,
					<a href="https://www.linkedin.com/company/patentinsights/" target="_blank" rel="noopener" class="hover:text-foreground transition-colors">Patent Insights by depa.tech</a>
				</span>
			</div>
		</div>
	</footer>
</div>
