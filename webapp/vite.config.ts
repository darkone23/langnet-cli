import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export const allowedHosts = ['langnet.computerdream.club', 'project-orion.net'];

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		host: '0.0.0.0',
		port: 43210,
		allowedHosts
	},
	preview: {
		allowedHosts
	}
});
