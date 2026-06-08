export const ADMIN_ROLE = 'admin';
export const USER_ROLE = 'user';
export const PENDING_ROLE = 'pending';
export const SECURITY_CURATOR_ROLE = 'security_curator';

type RoleUser = {
	role?: string | null;
} | null | undefined;

export const isAdmin = (user: RoleUser): boolean => user?.role === ADMIN_ROLE;

export const isSecurityCurator = (user: RoleUser): boolean => user?.role === SECURITY_CURATOR_ROLE;

export const canAccessAdminPanel = (user: RoleUser): boolean =>
	isAdmin(user) || isSecurityCurator(user);

export const isReadOnlyAdmin = (user: RoleUser): boolean => isSecurityCurator(user);

export const isActiveAppRole = (user: RoleUser): boolean =>
	user?.role === USER_ROLE || canAccessAdminPanel(user);

export const roleLabel = (role: string | null | undefined): string => {
	if (role === SECURITY_CURATOR_ROLE) {
		return 'Куратор ИБ';
	}
	return role ?? '';
};
