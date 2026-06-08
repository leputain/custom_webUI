<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getAuditLogs, getAuditStatus, getSecurityVersions } from '$lib/apis/security';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Refresh from '$lib/components/icons/Refresh.svelte';

	const i18n = getContext('i18n');

	let auditStatus: Record<string, any> | null = null;
	let auditLogs: Record<string, any> | null = null;
	let versions: Record<string, any> | null = null;
	let loading = true;
	let logsLoading = false;
	let search = '';

	const formatValue = (value: any) => {
		if (value === null || value === undefined || value === '') return '-';
		if (Array.isArray(value)) return value.length ? value.join(', ') : '-';
		if (typeof value === 'boolean') return value ? 'true' : 'false';
		if (typeof value === 'object') return JSON.stringify(value);
		return String(value);
	};

	const formatTimestamp = (value: any) => {
		if (!value) return '-';
		const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
		if (Number.isNaN(date.getTime())) return String(value);
		return date.toLocaleString();
	};

	const actorName = (entry: Record<string, any>) => {
		const actor = entry.actor ?? entry.user ?? {};
		return actor.email || actor.name || actor.id || '-';
	};

	const actorRole = (entry: Record<string, any>) => {
		const actor = entry.actor ?? entry.user ?? {};
		return actor.role || entry.actor_type || '-';
	};

	const targetLabel = (entry: Record<string, any>) => {
		const target = entry.target ?? {};
		if (target.email) return target.email;
		if (target.id) return target.id;
		if (target.type) return target.type;
		return formatValue(target);
	};

	const loadLogs = async () => {
		logsLoading = true;
		try {
			auditLogs = await getAuditLogs(localStorage.token, {
				limit: 100,
				offset: 0,
				search
			});
		} catch (error) {
			toast.error(`${error}`);
		}
		logsLoading = false;
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
			await loadLogs();
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
	<div class="flex flex-col gap-8 text-sm">
		<section>
			<div class="flex items-center justify-between gap-3 mb-3">
				<div class="text-base font-medium">{$i18n.t('Security Audit')}</div>
				<button
					type="button"
					class="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850"
					on:click={load}
					disabled={loading || logsLoading}
					title={$i18n.t('Refresh')}
				>
					<Refresh className="size-3.5" />
					<span>{$i18n.t('Refresh')}</span>
				</button>
			</div>

			<div class="text-sm font-medium mb-2">{$i18n.t('Audit Status')}</div>
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
			<div class="flex items-center justify-between gap-3 mb-3">
				<div class="text-sm font-medium">{$i18n.t('Audit Log')}</div>
				<div class="flex items-center gap-2">
					<label class="sr-only" for="audit-log-search">{$i18n.t('Search')}</label>
					<input
						id="audit-log-search"
						class="w-48 rounded-lg border border-gray-200 dark:border-gray-800 bg-transparent px-2 py-1 text-xs outline-hidden"
						bind:value={search}
						placeholder={$i18n.t('Search')}
						on:keydown={(event) => {
							if (event.key === 'Enter') {
								loadLogs();
							}
						}}
					/>
					<button
						type="button"
						class="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850"
						on:click={loadLogs}
						disabled={logsLoading}
						title={$i18n.t('Refresh')}
					>
						{#if logsLoading}
							<Spinner className="size-3.5" />
						{:else}
							<Refresh className="size-3.5" />
						{/if}
						<span>{$i18n.t('Refresh')}</span>
					</button>
				</div>
			</div>

			{#if auditLogs?.file_exists === false}
				<div class="text-gray-500 py-2">{auditLogs?.message ?? $i18n.t('Audit log file does not exist yet')}</div>
			{:else if (auditLogs?.items ?? []).length === 0}
				<div class="text-gray-500 py-2">{$i18n.t('No audit log records found')}</div>
			{:else}
				<div class="overflow-x-auto border border-gray-100 dark:border-gray-850 rounded-lg">
					<table class="min-w-full text-xs">
						<thead class="bg-gray-50 dark:bg-gray-900 text-gray-500">
							<tr>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Timestamp')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Event Type')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Outcome')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Actor')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Actor Role')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Target')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Method')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Request URI')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Source IP')}</th>
								<th class="text-left font-medium px-3 py-2">{$i18n.t('Status')}</th>
							</tr>
						</thead>
						<tbody>
							{#each auditLogs?.items ?? [] as entry}
								<tr class="border-t border-gray-100 dark:border-gray-850 align-top">
									<td class="px-3 py-2 whitespace-nowrap">{formatTimestamp(entry.timestamp)}</td>
									<td class="px-3 py-2 whitespace-nowrap">{formatValue(entry.event_type)}</td>
									<td class="px-3 py-2 whitespace-nowrap">{formatValue(entry.outcome)}</td>
									<td class="px-3 py-2 whitespace-nowrap">{actorName(entry)}</td>
									<td class="px-3 py-2 whitespace-nowrap">{actorRole(entry)}</td>
									<td class="px-3 py-2 max-w-64 break-all">{targetLabel(entry)}</td>
									<td class="px-3 py-2 whitespace-nowrap">{formatValue(entry.verb)}</td>
									<td class="px-3 py-2 max-w-96 break-all">{formatValue(entry.request_uri)}</td>
									<td class="px-3 py-2 whitespace-nowrap">{formatValue(entry.source_ip)}</td>
									<td class="px-3 py-2 whitespace-nowrap">{formatValue(entry.response_status_code)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</section>

		<section>
			<div class="text-sm font-medium mb-3">{$i18n.t('Versions')}</div>
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
