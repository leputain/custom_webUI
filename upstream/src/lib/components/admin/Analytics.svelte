<script>
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { canAccessAdminPanel } from '$lib/utils/rbac';

	import Dashboard from './Analytics/Dashboard.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if (!canAccessAdminPanel($user)) {
			await goto('/');
		}
		loaded = true;
	});
</script>

{#if loaded}
	<div class="w-full h-full pb-2 px-[16px]">
		<Dashboard />
	</div>
{/if}
