import { WEBUI_BASE_URL } from '$lib/constants';

const getJson = async (token: string, path: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}${path}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAuditStatus = async (token: string) =>
	getJson(token, '/api/v1/admin/security/audit/status');

export const getSecurityVersions = async (token: string) =>
	getJson(token, '/api/v1/admin/security/versions');
