import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		// Allow connections from the JupyterHub proxy
		allowedHosts: ['tip.epo.org']
	},
	test: {
		include: ['src/**/*.test.ts'],
		environment: 'jsdom',
		setupFiles: ['src/tests/setup.ts'],
		alias: {
			'$app/paths': new URL('./src/tests/mocks/app-paths.ts', import.meta.url).pathname,
			'$app/state': new URL('./src/tests/mocks/app-state.ts', import.meta.url).pathname,
			'$env/dynamic/private': new URL('./src/tests/mocks/env.ts', import.meta.url).pathname,
		}
	}
});
