import { RouterProvider, createBrowserRouter, Navigate } from "react-router-dom";
import { useAuth } from "../services/auth/authProvider";
import { ProtectedRoute } from "./ProtectedRoute";

import Login from '../pages/Login';
import QuickCheck from "../pages/blacklist/QuickCheck";
import DashboardLayout from "../layouts/dashboard/layout";
import BlacklistCheck from "../pages/dashboard/BlacklistCheck";
import BlacklistMonitor from "../pages/dashboard/BlacklistMonitor";
import ViewReport from "../pages/dashboard/ViewReport";
import Home from "../pages/dashboard/Home";
import AbuseIPDB from "../pages/dashboard/AbuseIPDB";
import Whois from "../pages/dashboard/Whois";
import ServerStatus from "../pages/dashboard/ServerStatus";

// New pages
import SubnetList from "../pages/subnets/SubnetList";
import SubnetDetail from "../pages/subnets/SubnetDetail";
import ScanHistory from "../pages/scans/ScanHistory";
import ApiKeys from "../pages/settings/ApiKeys";
import Webhooks from "../pages/settings/Webhooks";
import Alerts from "../pages/settings/Alerts";

const Routes = () => {
  const { token } = useAuth();

  const routesForPublic = [
    {
      path: '/',
      element: <Navigate to="/login" replace />,
    },
    {
      path: 'quick-check',
      element: <QuickCheck />
    }
  ];

  const routesForAuthenticatedOnly = [
    {
      path: '/dashboard',
      element: <ProtectedRoute />,
      children: [
        {
          element: <DashboardLayout />,
          children: [
            {
              index: true,
              element: <Home />
            },
            {
              path: 'blacklist-check',
              element: <BlacklistCheck />
            },
            {
              path: 'blacklist-monitor',
              element: <BlacklistMonitor />
            },
            {
              path: 'blacklist-monitor/report',
              element: <ViewReport />
            },
            {
              path: 'abuseipdb',
              element: <AbuseIPDB />
            },
            {
              path: 'whois',
              element: <Whois />
            },
            {
              path: 'server-status',
              element: <ServerStatus />
            },
            // New routes
            {
              path: 'subnets',
              element: <SubnetList />
            },
            {
              path: 'subnets/:subnetId',
              element: <SubnetDetail />
            },
            {
              path: 'scans',
              element: <ScanHistory />
            },
            {
              path: 'settings/api-keys',
              element: <ApiKeys />
            },
            {
              path: 'settings/webhooks',
              element: <Webhooks />
            },
            {
              path: 'settings/alerts',
              element: <Alerts />
            },
          ]
        },
      ],
    },
  ];

  const routesForNotAuthenticatedOnly = [
    {
      path: '/login',
      element: <Login />
    },
  ];

  const router = createBrowserRouter([
    ...routesForPublic,
    ...(!token ? routesForNotAuthenticatedOnly : []),
    ...routesForAuthenticatedOnly,
  ]);

  return <RouterProvider router={router} />;
}

export default Routes;
