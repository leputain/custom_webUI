<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getAuditStatus, getSecurityVersions } from '$lib/apis/security';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let auditStatus = null;
	let versions = null;
	let loading = true;

	const formatValue = (value) => {
		if (value === null || value === undefined || value === '') return '-';
		if (Array.isArray(value)) return value.length ? value.join(', ') : '-';
		if (typeof value === 'boolean') return value ? 'true' : 'false';
		return String(value);
	};

	const load = async () => {
		loading = true;
		try {
			const [audit, versionInfo] = await Promise.all([
				getAuditStatus(localStorage.token),
				getSecurityVersions(localStorage.token)
			]);
			auditStatus = audit;
			versions = versionInfo;
		} catch (error) {
			toast.error(`${error}`);
		}
		loading = false;
	};

	onMount(load);
</script>

{#if loading}
	<div class="my-10">
		<Spinner className="size-5" />
	</div>
{:else}
	<div class="flex flex-col gap-6 text-sm">
		<section>
			<div class="text-base font-medium mb-3">{$i18n.t('Security')} / {$i18n.t('Audit')}</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">
				{#each [
					['enabled', 'Enabled'],
					['audit_level', 'Audit Level'],
					['file_enabled', 'File Enabled'],
					['stdout_enabled', 'Stdout Enabled'],
					['file_path', 'File Path'],
					['rotation_size', 'Rotation Size'],
					['retention_days', 'Retention Days'],
					['included_paths', 'Included Paths'],
					['excluded_paths', 'Excluded Paths'],
					['get_requests_enabled', 'GET Requests Enabled'],
					['max_body_log_size', 'Max Body Log Size']
				] as field}
					<div class="flex justify-between gap-4 border-b border-gray-100 dark:border-gray-850 py-1">
						<div class="text-gray-500">{$i18n.t(field[1])}</div>
						<div class="text-right break-all">{formatValue(auditStatus?.[field[0]])}</div>
					</div>
				{/each}
			</div>
		</section>

		<section>
			<div class="text-base font-medium mb-3">{$i18n.t('Security')} / {$i18n.t('Versions')}</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">
				{#each [
					['open_webui_version', 'Open WebUI Version'],
					['backend_version', 'Backend Version'],
					['frontend_package_version', 'Frontend Version'],
					['python_version', 'Python Version'],
					['update_check_enabled', 'Update Check Enabled'],
					['offline_mode', 'Offline Mode'],
					['latest_available_version', 'Latest Available Version']
				] as field}
					<div class="flex justify-between gap-4 border-b border-gray-100 dark:border-gray-850 py-1">
						<div class="text-gray-500">{$i18n.t(field[1])}</div>
						<div class="text-right break-all">{formatValue(versions?.[field[0]])}</div>
					</div>
				{/each}
			</div>

			<div class="mt-5 text-sm font-medium">{$i18n.t('Critical Dependencies')}</div>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 mt-2">
				{#each Object.entries(versions?.critical_dependencies ?? {}) as [name, version]}
					<div class="flex justify-between gap-4 border-b border-gray-100 dark:border-gray-850 py-1">
						<div class="text-gray-500">{name}</div>
						<div>{version}</div>
					</div>
				{/each}
			</div>
		</section>
	</div>
{/if}
