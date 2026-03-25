<script lang="ts">
	import { base } from '$app/paths';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
</script>

<svelte:head>
	<title>About | PATSTAT Explorer</title>
</svelte:head>

<div class="space-y-8 max-w-3xl mx-auto">
	<!-- Header -->
	<div class="space-y-3">
		<h1 class="text-3xl font-bold">About PATSTAT Explorer</h1>
		<p class="text-muted-foreground leading-relaxed">
			A tool for searching and analysing patent data from the EPO PATSTAT database.
			Built for the EPO Technology &amp; Innovation Programme (TIP) by
			<a href="https://mtc.berlin" target="_blank" rel="noopener" class="text-[var(--mtc-blue)] hover:underline font-medium">mtc.berlin</a>.
		</p>
	</div>

	<!-- What you can do -->
	<Card.Root>
		<Card.Header>
			<Card.Title>What you can do</Card.Title>
		</Card.Header>
		<Card.Content class="space-y-4 text-sm leading-relaxed">
			<div>
				<h3 class="font-semibold mb-1">Search &amp; consolidate applicants</h3>
				<p class="text-muted-foreground">
					Find patent applicants by name. PATSTAT contains many variants for the same organization
					(SIEMENS AG, SIEMENS LTD, SIEMENS CORP, etc.). The search lets you group these variants
					and analyse them as a single entity.
				</p>
			</div>
			<div>
				<h3 class="font-semibold mb-1">Analyse filing activity</h3>
				<p class="text-muted-foreground">
					See how an applicant's patent portfolio developed over time. Compare filing activity
					across jurisdictions and technology fields (CPC classification).
				</p>
			</div>
			<div>
				<h3 class="font-semibold mb-1">Explore networks &amp; citations</h3>
				<p class="text-muted-foreground">
					Visualise who files patents together (co-applicant network) and who cites whom
					(citation flow). Identify collaboration patterns and technology dependencies.
				</p>
			</div>
			<div>
				<h3 class="font-semibold mb-1">Compare technologies &amp; countries</h3>
				<p class="text-muted-foreground">
					Browse patent activity by CPC code. Compare filing trends across countries.
					See which technology areas overlap in an applicant's portfolio (co-occurrence heatmap).
				</p>
			</div>
			<div>
				<h3 class="font-semibold mb-1">Ask questions in natural language</h3>
				<p class="text-muted-foreground">
					The AI Query interface lets you ask questions about patent data in plain language.
					It uses the
					<a href="https://github.com/mtcberlin/mtc-patstat-mcp-lite" target="_blank" rel="noopener"
						class="text-[var(--mtc-blue)] hover:underline">mtc.berlin PATSTAT MCP</a>
					server to explore the database schema, build SQL, and execute queries -all visible
					step by step. Bring your own Anthropic API key.
				</p>
			</div>
		</Card.Content>
	</Card.Root>

	<!-- How it works -->
	<Card.Root>
		<Card.Header>
			<Card.Title>How it works</Card.Title>
		</Card.Header>
		<Card.Content class="space-y-3 text-sm text-muted-foreground leading-relaxed">
			<p>
				PATSTAT Explorer runs on the EPO TIP JupyterHub. It connects to the PATSTAT database
				on Google BigQuery through the TIP PatstatClient library. The app is a
				<a href="https://svelte.dev/docs/kit" target="_blank" rel="noopener" class="text-[var(--mtc-blue)] hover:underline">SvelteKit</a>
				web application with a Python backend.
			</p>
			<p>
				All analysis context (selected applicants, filters, consolidations) is encoded in the URL.
				This means every view is bookmarkable and shareable -just copy the URL.
			</p>
			<p>
				For the AI Query feature, the app runs a local
				<a href="https://modelcontextprotocol.io" target="_blank" rel="noopener" class="text-[var(--mtc-blue)] hover:underline">MCP</a>
				(Model Context Protocol) server that gives Claude access to the PATSTAT schema.
				Claude explores table structures, writes SQL, and runs queries -you can watch each step.
			</p>
		</Card.Content>
	</Card.Root>

	<!-- CTA -->
	<Card.Root class="bg-gradient-to-br from-[var(--mtc-navy)] to-[var(--mtc-blue)] text-white">
		<Card.Content class="py-8 text-center space-y-4">
			<h2 class="text-xl font-bold">Need a custom patent analysis?</h2>
			<p class="text-white/80 text-sm max-w-md mx-auto leading-relaxed">
				We build tailored patent landscape reports, set up PATSTAT on BigQuery,
				and develop custom analysis tools. Let's talk about your use case.
			</p>
			<div class="flex flex-wrap gap-3 justify-center pt-2">
				<a
					href="https://calendly.com/arne-krueger-mtc"
					target="_blank" rel="noopener"
					class="inline-flex items-center rounded-lg bg-white px-4 py-2 text-sm font-medium text-[var(--mtc-navy)] shadow-sm hover:bg-white/90 transition-colors"
				>
					Book a call
				</a>
				<a
					href="https://mtc.berlin"
					target="_blank" rel="noopener"
					class="inline-flex items-center rounded-lg border border-white/30 px-4 py-2 text-sm font-medium text-white hover:bg-white/10 transition-colors"
				>
					mtc.berlin
				</a>
				<a
					href="https://patentreports.depa.tech"
					target="_blank" rel="noopener"
					class="inline-flex items-center rounded-lg border border-white/30 px-4 py-2 text-sm font-medium text-white hover:bg-white/10 transition-colors"
				>
					Patent Intelligence Reports
				</a>
			</div>
		</Card.Content>
	</Card.Root>

	<!-- Tech stack (compact) -->
	<div class="text-xs text-muted-foreground text-center space-y-1 pb-4">
		<p>
			Built with SvelteKit, Tailwind CSS, D3.js, LayerChart, FastAPI, and the Anthropic Claude API.
		</p>
		<p>
			Source:
			<a href="https://github.com/mtcberlin/epo-tip-svelte-patstat-explorer" target="_blank" rel="noopener"
				class="text-[var(--mtc-blue)] hover:underline">github.com/mtcberlin/epo-tip-svelte-patstat-explorer</a>
		</p>
	</div>
</div>
