import {
	HiOutlineViewGrid,
	HiDesktopComputer,
	HiCheck,
	HiOutlineQuestionMarkCircle,
	HiShieldExclamation,
	HiGlobe,
	HiStatusOnline
} from 'react-icons/hi'
import { HiServerStack, HiClock, HiKey, HiBell, HiLink } from 'react-icons/hi2'

export const DASHBOARD_SIDEBAR_LINKS = [
	{
		key: 'dashboard',
		label: 'Dashboard',
		path: '/dashboard',
		icon: <HiOutlineViewGrid />
	},
	{
		key: 'subnets',
		label: 'Subnet Monitoring',
		path: '/dashboard/subnets',
		icon: <HiServerStack />
	},
	{
		key: 'scans',
		label: 'Scan History',
		path: '/dashboard/scans',
		icon: <HiClock />
	},
	{
		key: 'blacklist-monitor',
		label: 'Blacklist Monitor',
		path: '/dashboard/blacklist-monitor',
		icon: <HiDesktopComputer />
	},
	{
		key: 'blacklist-check',
		label: 'Blacklist Check',
		path: '/dashboard/blacklist-check',
		icon: <HiCheck />
	},
	{
		key: 'abuseipdb',
		label: 'AbuseIPDB',
		path: '/dashboard/abuseipdb',
		icon: <HiShieldExclamation />
	},
	{
		key: 'whois',
		label: 'WHOIS Lookup',
		path: '/dashboard/whois',
		icon: <HiGlobe />
	},
	{
		key: 'server-status',
		label: 'Is Server Up?',
		path: '/dashboard/server-status',
		icon: <HiStatusOnline />
	},
	{
		key: 'divider-settings',
		label: '--- Settings ---',
		divider: true,
	},
	{
		key: 'api-keys',
		label: 'API Keys',
		path: '/dashboard/settings/api-keys',
		icon: <HiKey />
	},
	{
		key: 'webhooks',
		label: 'Webhooks',
		path: '/dashboard/settings/webhooks',
		icon: <HiLink />
	},
	{
		key: 'alerts',
		label: 'Alert Rules',
		path: '/dashboard/settings/alerts',
		icon: <HiBell />
	}
]

export const DASHBOARD_SIDEBAR_BOTTOM_LINKS = [
	{
		key: 'support',
		label: 'API Docs',
		path: '/api/swagger/',
		icon: <HiOutlineQuestionMarkCircle />
	}
]
