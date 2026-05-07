import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/lib/theme-provider";
import Landing from "@/pages/landing";
import Login from "@/pages/login";
import Signup from "@/pages/signup";
import DashboardOverview from "@/pages/dashboard/overview";
import DashboardMap from "@/pages/dashboard/map";
import DashboardTrends from "@/pages/dashboard/trends";
import DashboardForecast from "@/pages/dashboard/forecast";
import DashboardData from "@/pages/dashboard/data";
import AreaAnalysis from "@/pages/area-analysis";
import NotFound from "@/pages/not-found";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Landing} />
      <Route path="/login" component={Login} />
      <Route path="/signup" component={Signup} />
      {/* Dashboard pages — each route mounts its own DashboardLayout (sidebar
          + shared queries). Wouter matches in order, so place specific
          /dashboard/* paths before the catch-all /dashboard. */}
      <Route path="/dashboard/map" component={DashboardMap} />
      <Route path="/dashboard/trends" component={DashboardTrends} />
      <Route path="/dashboard/forecast" component={DashboardForecast} />
      <Route path="/dashboard/data" component={DashboardData} />
      <Route path="/dashboard" component={DashboardOverview} />
      <Route path="/area/:areaId" component={AreaAnalysis} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="light">
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
