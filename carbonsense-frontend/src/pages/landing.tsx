import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";
import { useLocation } from "wouter";
import {
  Leaf,
  ArrowRight,
  Check,
  CheckCircle,
  MapPin,
  Zap,
  Calendar,
  Play,
  Target,
  TrendingUp,
  Users,
  Database,
  Brain,
  BarChart3,
  Download,
  Quote,
} from "lucide-react";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";

export default function Landing() {
  const [, setLocation] = useLocation();

  const sectors = [
    { label: "Transport", color: "bg-blue-500" },
    { label: "Industry", color: "bg-purple-500" },
    { label: "Energy", color: "bg-amber-500" },
    { label: "Waste", color: "bg-orange-500" },
    { label: "Buildings", color: "bg-pink-500" },
  ];

  const capabilities = [
    {
      icon: MapPin,
      title: "Neighborhood-Level Data",
      description:
        "Drill down into 50+ areas across Lahore with detailed emission breakdowns by sector.",
    },
    {
      icon: TrendingUp,
      title: "Historical Trends",
      description:
        "Analyze 3+ years of emission data to understand patterns and seasonal variations.",
    },
    {
      icon: Brain,
      title: "Time-Series Forecasting",
      description:
        "SARIMA & Holt-Winters models with 94% accuracy for 12-month emission forecasts.",
    },
    {
      icon: Download,
      title: "Open Data Access",
      description:
        "Export all data in CSV format for research, reports, and custom analysis.",
    },
  ];

  const testimonials = [
    {
      quote:
        "Finally, we have the granular emissions data we needed to design targeted interventions for Lahore.",
      author: "Dr. Fatima Khan",
      role: "Climate Scientist, PIDE",
      image: "👩‍🔬",
    },
    {
      quote:
        "CarbonSense's forecasting helped us predict the impact of our transit initiative before implementation.",
      author: "Ahmed Malik",
      role: "City Planner, Lahore Metropolitan Authority",
      image: "👨‍💼",
    },
    {
      quote:
        "I've never seen emissions data presented this clearly. Finally, I can explain climate challenges to my constituents.",
      author: "Zainab Ali",
      role: "Environmental Advocate",
      image: "👩‍🌾",
    },
  ];

  const faqs = [
    {
      q: "Where does the emissions data come from?",
      a: "We use Climate Trace, a global coalition that combines satellite imagery, remote sensing, and AI to independently track greenhouse gas emissions.",
    },
    {
      q: "How accurate are the ML predictions?",
      a: "We use SARIMA and Holt-Winters Exponential Smoothing models, automatically selecting the best performer based on R² and RMSE validation metrics. Our models achieve approximately 94% accuracy with 95% confidence intervals.",
    },
    {
      q: "Can I export the data?",
      a: "Yes! All emission data is available for download in CSV format through our Data Export feature in the dashboard.",
    },
    {
      q: "What sectors are tracked?",
      a: "We track emissions across 5 key sectors: Transport, Industry, Energy, Waste, and Buildings - covering the major sources of carbon emissions in urban areas.",
    },
    {
      q: "How far ahead can you forecast?",
      a: "Our ML models generate forecasts for up to 12 months into the future, helping policymakers plan proactive interventions.",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* ============ NAVIGATION ============ */}
      <nav className="sticky top-0 z-50 bg-background/95 backdrop-blur border-b">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-emerald-600 flex items-center justify-center">
              <Leaf className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-lg">CarbonSense</span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setLocation("/login")}
              data-testid="button-nav-login"
            >
              Sign In
            </Button>
            <Button
              size="sm"
              onClick={() => setLocation("/signup")}
              data-testid="button-nav-signup"
            >
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* ============ HERO SECTION ============ */}
      <section className="py-20 px-4 relative overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 -z-10" />

        <div className="max-w-6xl mx-auto">
          {/* Trust badge */}
          <div className="flex items-center justify-center mb-6">
            <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-4 py-1.5 rounded-full border border-emerald-200 dark:border-emerald-800">
              🌍 AI-Powered Carbon Emission Monitoring & Forecasting
            </span>
          </div>

          <div className="max-w-3xl mx-auto text-center mb-12">
            {/* Main headline */}
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-4 leading-tight">
              See Where Lahore's{" "}
              <span className="text-emerald-600 dark:text-emerald-400">
                Carbon Emissions
              </span>{" "}
              Come From
            </h1>

            {/* Subheading */}
            <p className="text-xl text-muted-foreground mb-8 leading-relaxed max-w-2xl mx-auto">
              Comprehensive emissions data across 5 sectors. AI-powered
              predictions. Actionable insights for policymakers, researchers,
              and climate advocates.
            </p>

            {/* Trust indicators */}
            <div className="flex flex-wrap justify-center gap-6 mb-10 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-emerald-600" />
                <span>Science-backed data</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-emerald-600" />
                <span>Climate Trace data</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-emerald-600" />
                <span>Free access</span>
              </div>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-wrap justify-center gap-4 mb-8">
              <Button
                size="lg"
                onClick={() => setLocation("/dashboard")}
                className="bg-emerald-600 hover:bg-emerald-700 px-8"
                data-testid="button-view-dashboard"
              >
                Explore Live Dashboard
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => setLocation("/signup")}
                className="px-8"
                data-testid="button-hero-signup"
              >
                Join the Community
              </Button>
            </div>
          </div>

          {/* Sector tags */}
          <div className="flex flex-wrap justify-center gap-2">
            {sectors.map((sector) => (
              <span
                key={sector.label}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-sm font-medium"
              >
                <span className={`h-2.5 w-2.5 rounded-full ${sector.color}`} />
                {sector.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ============ VALUE PROPOSITION ============ */}
      <section className="py-16 px-4 border-b">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Target,
                title: "For Policymakers",
                description:
                  "Data-driven insights to design effective climate interventions and track policy impact.",
              },
              {
                icon: TrendingUp,
                title: "For Researchers",
                description:
                  "Access verified emissions data across 50+ areas. Export and analyze with confidence.",
              },
              {
                icon: Users,
                title: "For Citizens",
                description:
                  "Understand your city's emissions profile and join the climate action movement.",
              },
            ].map((item) => (
              <div key={item.title} className="flex flex-col gap-3">
                <div className="h-12 w-12 rounded-lg bg-emerald-100 dark:bg-emerald-950/50 flex items-center justify-center">
                  <item.icon className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="font-semibold text-lg">{item.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ STATS SECTION ============ */}
      <section className="py-12 px-4 border-y bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {[
              { number: "50+", label: "Areas Monitored", icon: MapPin },
              { number: "5", label: "Emission Sectors", icon: Zap },
              { number: "3+", label: "Years of Data", icon: Calendar },
              { number: "94%", label: "ML Accuracy", icon: Brain },
            ].map((stat) => (
              <div
                key={stat.label}
                className="flex flex-col items-center gap-3"
              >
                <stat.icon className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                <div className="text-3xl md:text-4xl font-bold text-emerald-600 dark:text-emerald-400">
                  {stat.number}
                </div>
                <div className="text-sm text-muted-foreground">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ CAPABILITIES SECTION ============ */}
      <section className="py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="mb-12 text-center">
            <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-2">
              PLATFORM CAPABILITIES
            </p>
            <h2 className="text-3xl font-bold mb-3">
              Built for Climate Intelligence
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Advanced technology powering actionable environmental insights
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {capabilities.map((item) => (
              <div key={item.title} className="text-center p-6">
                <div className="h-14 w-14 rounded-2xl bg-emerald-100 dark:bg-emerald-950/50 flex items-center justify-center mb-4 mx-auto">
                  <item.icon className="h-7 w-7 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="font-semibold mb-2 text-base">{item.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>

          {/* CTA to Dashboard */}
          <div className="mt-12 text-center">
            <Button
              size="lg"
              onClick={() => setLocation("/dashboard")}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              Try It Now - Free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>

      {/* ============ FEATURE SHOWCASE WITH SCREENSHOTS ============ */}
      <section className="py-16 px-4 bg-muted/40">
        <div className="max-w-6xl mx-auto">
          <div className="mb-12 text-center">
            <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-2">
              SEE IT IN ACTION
            </p>
            <h2 className="text-3xl font-bold mb-3">Explore the Platform</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Powerful visualizations that make complex emission data easy to
              understand
            </p>
          </div>

          {/* Feature 1: Interactive Map */}
          <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
            <div className="order-2 lg:order-1">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 text-sm font-medium mb-4">
                <MapPin className="h-4 w-4" />
                Interactive Map
              </div>
              <h3 className="text-2xl font-bold mb-3">
                Visualize Emission Hotspots
              </h3>
              <p className="text-muted-foreground mb-4 leading-relaxed">
                Our color-coded map shows emission intensity across Lahore's
                neighborhoods. Click any area to see detailed breakdowns by
                sector, historical trends, and AI-powered recommendations.
              </p>
              <ul className="space-y-2 text-sm">
                {[
                  "50+ monitored areas",
                  "Historical & forecast data",
                  "Sector-wise breakdown",
                  "Click for detailed analysis",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-emerald-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="order-1 lg:order-2">
              <div className="rounded-xl overflow-hidden border border-border shadow-lg">
                <img
                  src="/images/feature-map.png"
                  alt="Interactive emission map showing Lahore neighborhoods"
                  className="w-full h-auto"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = "none";
                    target.parentElement!.innerHTML += `
                      <div class="aspect-video bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/50 dark:to-teal-950/50 flex items-center justify-center p-8">
                        <div class="text-center">
                          <div class="h-12 w-12 rounded-xl bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center mx-auto mb-3">
                            <svg class="h-6 w-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                          </div>
                          <p class="text-emerald-600 dark:text-emerald-400 font-medium">Map Screenshot</p>
                          <p class="text-xs text-muted-foreground mt-1">public/images/feature-map.png</p>
                        </div>
                      </div>
                    `;
                  }}
                />
              </div>
            </div>
          </div>

          {/* Feature 2: Trend Analysis */}
          <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
            <div>
              <div className="rounded-xl overflow-hidden border border-border shadow-lg">
                <img
                  src="/images/feature-trends.png"
                  alt="Trend analysis charts showing emission patterns"
                  className="w-full h-auto"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = "none";
                    target.parentElement!.innerHTML += `
                      <div class="aspect-video bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 flex items-center justify-center p-8">
                        <div class="text-center">
                          <div class="h-12 w-12 rounded-xl bg-blue-100 dark:bg-blue-900 flex items-center justify-center mx-auto mb-3">
                            <svg class="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
                          </div>
                          <p class="text-blue-600 dark:text-blue-400 font-medium">Trends Screenshot</p>
                          <p class="text-xs text-muted-foreground mt-1">public/images/feature-trends.png</p>
                        </div>
                      </div>
                    `;
                  }}
                />
              </div>
            </div>
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 text-sm font-medium mb-4">
                <TrendingUp className="h-4 w-4" />
                Trend Analysis
              </div>
              <h3 className="text-2xl font-bold mb-3">
                Track Historical Patterns
              </h3>
              <p className="text-muted-foreground mb-4 leading-relaxed">
                Analyze how emissions have changed over time. Compare sectors,
                identify seasonal patterns, and measure the impact of policy
                changes with interactive charts.
              </p>
              <ul className="space-y-2 text-sm">
                {[
                  "3+ years of historical data",
                  "Sector-by-sector comparison",
                  "Seasonal pattern detection",
                  "Year-over-year analysis",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-blue-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Feature 3: ML Forecasting */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="order-2 lg:order-1">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-100 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 text-sm font-medium mb-4">
                <Brain className="h-4 w-4" />
                AI Recommendations
              </div>
              <h3 className="text-2xl font-bold mb-3">
                AI-Powered Recommendations
              </h3>
              <p className="text-muted-foreground mb-4 leading-relaxed">
                Get personalized, actionable recommendations powered by Gemini
                AI. Our system analyzes emission patterns and provides
                sector-specific strategies to reduce your carbon footprint.
              </p>
              <ul className="space-y-2 text-sm">
                {[
                  "Gemini AI-powered insights",
                  "Sector-specific strategies",
                  "Actionable reduction plans",
                  "Priority-ranked suggestions",
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-purple-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="order-1 lg:order-2">
              <div className="rounded-xl overflow-hidden border border-border shadow-lg">
                <img
                  src="/images/feature-forecast.png"
                  alt="ML forecasting showing predicted emission trends"
                  className="w-full h-auto"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = "none";
                    target.parentElement!.innerHTML += `
                      <div class="aspect-video bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950/50 dark:to-pink-950/50 flex items-center justify-center p-8">
                        <div class="text-center">
                          <div class="h-12 w-12 rounded-xl bg-purple-100 dark:bg-purple-900 flex items-center justify-center mx-auto mb-3">
                            <svg class="h-6 w-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
                          </div>
                          <p class="text-purple-600 dark:text-purple-400 font-medium">Forecast Screenshot</p>
                          <p class="text-xs text-muted-foreground mt-1">public/images/feature-forecast.png</p>
                        </div>
                      </div>
                    `;
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section className="py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold mb-3">How CarbonSense Works</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              From real-world emissions data to actionable climate intelligence.
              It only takes a few minutes to start exploring.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 relative">
            {/* Connecting line on desktop */}
            <div className="hidden md:block absolute top-12 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-emerald-300 to-transparent" />

            {[
              {
                step: "01",
                title: "Collect & Aggregate",
                description:
                  "We gather emissions data from Climate Trace, which uses satellite imagery, remote sensing, and AI to independently track greenhouse gas emissions.",
                icon: Database,
              },
              {
                step: "02",
                title: "Analyze with AI",
                description:
                  "Machine learning identifies patterns, trends, and anomalies in the emissions data.",
                icon: Brain,
              },
              {
                step: "03",
                title: "Visualize & Share",
                description:
                  "Interactive dashboards make complex data accessible to decision-makers and communities.",
                icon: BarChart3,
              },
            ].map((item) => (
              <div key={item.step} className="relative z-10">
                <div className="flex gap-4 mb-4">
                  <div className="flex-shrink-0">
                    <div className="h-12 w-12 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold shadow-lg">
                      {item.step}
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">{item.title}</h3>
                  </div>
                </div>
                <p className="text-muted-foreground leading-relaxed ml-16 text-sm">
                  {item.description}
                </p>
                <div className="mt-4 ml-16">
                  <item.icon className="h-8 w-8 text-emerald-100 dark:text-emerald-900" />
                </div>
              </div>
            ))}
          </div>

          {/* Bottom CTA */}
          <div className="mt-12 text-center">
            <Button
              size="lg"
              variant="outline"
              onClick={() => setLocation("/dashboard")}
            >
              See It in Action
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>

      {/* ============ DATA-DRIVEN CLIMATE ACTION ============ */}
      <section className="py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-3">
                WHY IT MATTERS
              </p>
              <h2 className="text-3xl font-bold mb-4">
                Turn Emissions Data Into Climate Action
              </h2>
              <p className="text-lg text-muted-foreground mb-6 leading-relaxed">
                Lahore faces significant air quality challenges. CarbonSense
                helps you understand the root causes, measure progress, and
                demonstrate the impact of climate interventions.
              </p>

              <ul className="space-y-4 mb-8">
                {[
                  {
                    label: "Policymakers",
                    detail:
                      "Design evidence-based climate policies with real emissions data",
                  },
                  {
                    label: "Researchers",
                    detail:
                      "Analyze trends and publish peer-reviewed climate science",
                  },
                  {
                    label: "Advocates",
                    detail:
                      "Make a compelling case for climate action with verified data",
                  },
                  {
                    label: "Businesses",
                    detail:
                      "Track corporate emissions and plan reduction strategies",
                  },
                ].map((item) => (
                  <li key={item.label} className="flex gap-3">
                    <Check className="h-5 w-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-sm">{item.label}</div>
                      <div className="text-sm text-muted-foreground">
                        {item.detail}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>

              <Button
                size="lg"
                onClick={() => setLocation("/signup")}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                Get Started Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>

            {/* Data visualization card */}
            <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/50 dark:to-teal-950/50 border-emerald-200 dark:border-emerald-800 overflow-hidden">
              <CardContent className="p-8">
                <div className="mb-8">
                  <h3 className="font-semibold text-lg mb-4">
                    Reduction Potential by Sector
                  </h3>
                  <div className="space-y-4">
                    {[
                      { label: "Transport", current: 12.4, potential: 8 },
                      { label: "Industry", current: 18.3, potential: 15 },
                      { label: "Energy", current: 16.7, potential: 14 },
                    ].map((sector) => (
                      <div key={sector.label}>
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-sm font-medium">
                            {sector.label}
                          </span>
                          <span className="text-sm font-bold text-emerald-600">
                            -{sector.potential}%
                          </span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                          <div
                            className="bg-emerald-500 h-2 rounded-full"
                            style={{
                              width: `${
                                (sector.potential / sector.current) * 100
                              }%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-white dark:bg-black/20 border border-emerald-200 dark:border-emerald-800">
                  <p className="text-sm text-muted-foreground mb-1">
                    Average Potential
                  </p>
                  <div className="text-4xl font-bold text-emerald-600 dark:text-emerald-400">
                    -12.4%
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    If all sectors meet their reduction targets
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* ============ FAQ SECTION ============ */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">
            Frequently Asked Questions
          </h2>

          <div className="space-y-3">
            {faqs.map((faq, idx) => (
              <Accordion key={idx} type="single" collapsible>
                <AccordionItem value={`faq-${idx}`}>
                  <AccordionTrigger className="text-left font-semibold hover:text-emerald-600">
                    {faq.q}
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground">
                    {faq.a}
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            ))}
          </div>
        </div>
      </section>

      {/* ============ CTA SECTION ============ */}
      <section className="py-16 px-4 bg-emerald-600 dark:bg-emerald-700">
        <div className="max-w-6xl mx-auto text-center text-white">
          <h2 className="text-4xl font-bold mb-3">
            Start Monitoring Lahore's Emissions Today
          </h2>
          <p className="text-lg text-emerald-100 mb-8 max-w-2xl mx-auto leading-relaxed">
            Join researchers, policymakers, and climate advocates. Access
            powerful emissions analytics at no cost.
          </p>
          <div className="flex flex-wrap justify-center gap-4 mb-6">
            <Button
              size="lg"
              variant="secondary"
              onClick={() => setLocation("/signup")}
              className="px-8"
              data-testid="button-cta-signup"
            >
              Create Free Account
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button
              size="lg"
              variant="ghost"
              onClick={() => setLocation("/dashboard")}
              className="border border-white/50 text-white hover:bg-white/10 px-8"
              data-testid="button-cta-dashboard"
            >
              Explore Dashboard
            </Button>
          </div>

          {/* Trust line */}
          <p className="text-sm text-emerald-100">
            ✓ No credit card required • ✓ Free forever • ✓ Open data
          </p>
        </div>
      </section>

      {/* ============ FOOTER ============ */}
      <footer className="py-12 px-4 border-t bg-muted/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            {/* Brand */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="h-7 w-7 rounded-lg bg-emerald-600 flex items-center justify-center">
                  <Leaf className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="font-semibold">CarbonSense</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Environmental intelligence for a sustainable future
              </p>
            </div>

            {/* Resources */}
            <div>
              <h4 className="font-semibold mb-4 text-sm">Resources</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    Blog
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    Methodology
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    FAQ
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    Contact
                  </a>
                </li>
              </ul>
            </div>

            {/* Company */}
            <div>
              <h4 className="font-semibold mb-4 text-sm">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    About
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    Privacy Policy
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    Terms of Service
                  </a>
                </li>
                <li>
                  <a href="#" className="hover:text-emerald-600 transition">
                    Careers
                  </a>
                </li>
              </ul>
            </div>

            {/* Newsletter */}
            <div>
              <h4 className="font-semibold mb-4 text-sm">Newsletter</h4>
              <p className="text-sm text-muted-foreground mb-3">
                Get weekly climate insights and data stories
              </p>
              <input
                type="email"
                placeholder="Enter your email"
                className="w-full px-3 py-2 rounded-md bg-background border border-input text-sm mb-2"
              />
              <Button
                size="sm"
                className="w-full bg-emerald-600 hover:bg-emerald-700"
              >
                Subscribe
              </Button>
            </div>
          </div>

          {/* Bottom footer */}
          <div className="border-t pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              © 2025 CarbonSense. All rights reserved.
            </p>
            <div className="flex gap-4">
              <a
                href="#"
                className="text-muted-foreground hover:text-emerald-600 transition"
              >
                <span className="text-xl">𝕏</span>
              </a>
              <a
                href="#"
                className="text-muted-foreground hover:text-emerald-600 transition"
              >
                <span className="text-xl">f</span>
              </a>
              <a
                href="#"
                className="text-muted-foreground hover:text-emerald-600 transition"
              >
                <span className="text-xl">in</span>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
