import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf-8');

describe('admin security settings wiring', () => {
	it('registers Security Audit in admin settings tabs', () => {
		const settings = read('./Settings.svelte');

		expect(settings).toContain("id: 'security'");
		expect(settings).toContain("title: 'Security Audit'");
		expect(settings).toContain("route: '/admin/settings/security'");
		expect(settings).toContain('<Security />');
	});

	it('blocks mutation controls across admin settings for security_curator', () => {
		const settings = read('./Settings.svelte');

		expect(settings).toContain('isReadOnlyAdmin');
		expect(settings).toContain("selectedTab !== 'security'");
		expect(settings).toContain("querySelectorAll('input, textarea, select, button')");
		expect(settings).toContain("control.setAttribute('disabled', 'true')");
		expect(settings).toContain('blockReadOnlyInteraction');
		expect(settings).toContain('on:submit|capture={blockReadOnlyInteraction}');
	});

	it('renders audit status, audit log, and versions blocks', () => {
		const security = read('./Settings/Security.svelte');

		expect(security).toContain('getAuditStatus');
		expect(security).toContain('getAuditLogs');
		expect(security).toContain('getSecurityVersions');
		expect(security).toContain('Audit Status');
		expect(security).toContain('Audit Log');
		expect(security).toContain('Versions');
		expect(security).not.toContain('Delete Audit Log');
		expect(security).not.toContain('Clear Audit Log');
	});

	it('has Russian translations for security audit labels', () => {
		const translations = JSON.parse(read('../../i18n/locales/ru-RU/translation.json'));

		expect(translations['Security Audit']).toBe('Аудит безопасности');
		expect(translations['Audit Status']).toBe('Статус аудита');
		expect(translations['Audit Log']).toBe('Журнал аудита');
		expect(translations['Versions']).toBe('Версии');
	});
});
