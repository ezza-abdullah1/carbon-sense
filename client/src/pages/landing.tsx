import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLocation } from "wouter";
import { 
  Leaf, 
  TrendingDown, 
  BarChart3, 
  MapPin, 
  Lightbulb, 
  Users, 
  Target,
  ArrowRight
} from "lucide-react";

export default function Landing() {
  const [, setLocation] = useLocation();

  const features = [
    {
      icon: MapPin,
      title: "Interactive Map Visualization",
      description: "Explore Lahore's emission hotspots with color-coded areas showing real-time carbon footprint data across different neighborhoods.",
    },
    {
      icon: BarChart3,
      title: "Comprehensive Analytics",
      description: "Track emissions across five key sectors: transport, industry, energy, waste, and buildings with detailed time-series analysis.",
    },
    {
      icon: TrendingDown,
      title: "ML-Powered Forecasts",
      description: "Machine learning models predict future emission trends, helping policymakers plan effective interventions.",
    },
    {
      icon: Target,
      title: "Area Comparisons",
      description: "Compare emission levels between different localities with leaderboards and performance metrics.",
    },
    {
      icon: Lightbulb,
      title: "Data-Driven Insights",
      description: "Gain actionable insights from historical trends and patterns to inform environmental policy decisions.",
    },
    {
      icon: Users,
      title: "Public Awareness",
      description: "Promote transparency and community engagement in Lahore's journey toward carbon neutrality.",
    },
  ];

  return (
    <div className="min-h-screen">
      <nav className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Leaf className="h-6 w-6 text-primary" />
            <span className="font-semibold text-lg">Lahore Carbon Monitor</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              onClick={() => setLocation("/login")}
              data-testid="button-nav-login"
            >
              Sign In
            </Button>
            <Button
              onClick={() => setLocation("/signup")}
              data-testid="button-nav-signup"
            >
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-4">
            <Leaf className="h-4 w-4" />
            Environmental Intelligence Platform
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
            Visualizing Lahore's
            <span className="text-primary block">Carbon Footprint</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Real-time emissions monitoring and AI-powered forecasting for Lahore's urban areas. 
            Empowering data-driven environmental action across transport, industry, energy, waste, and buildings.
          </p>
          <div className="flex items-center justify-center gap-4 pt-4">
            <Button
              size="lg"
              onClick={() => setLocation("/dashboard")}
              className="group"
              data-testid="button-view-dashboard"
            >
              View Dashboard
              <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => setLocation("/signup")}
              data-testid="button-hero-signup"
            >
              Create Account
            </Button>
          </div>
        </div>
      </section>

      <section className="bg-muted/30 py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Platform Features</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Comprehensive tools for monitoring, analyzing, and forecasting carbon emissions across Lahore's diverse localities
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="hover-elevate">
                <CardHeader>
                  <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                    <feature.icon className="h-6 w-6 text-primary" />
                  </div>
                  <CardTitle className="text-xl">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">How It Works</h2>
            <p className="text-muted-foreground">
              Our platform combines cutting-edge technology with comprehensive data collection
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center space-y-3">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto text-2xl font-bold text-primary">
                1
              </div>
              <h3 className="font-semibold text-lg">Data Collection</h3>
              <p className="text-muted-foreground text-sm">
                Aggregate emissions data from sensors, government reports, and satellite imagery across Lahore's urban areas
              </p>
            </div>
            <div className="text-center space-y-3">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto text-2xl font-bold text-primary">
                2
              </div>
              <h3 className="font-semibold text-lg">ML Analysis</h3>
              <p className="text-muted-foreground text-sm">
                Apply machine learning algorithms to identify patterns, predict trends, and generate actionable insights
              </p>
            </div>
            <div className="text-center space-y-3">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto text-2xl font-bold text-primary">
                3
              </div>
              <h3 className="font-semibold text-lg">Visualization</h3>
              <p className="text-muted-foreground text-sm">
                Present data through interactive maps, charts, and dashboards for easy understanding and decision-making
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-primary/5 py-16">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-3xl mx-auto space-y-6">
            <h2 className="text-3xl font-bold">Ready to Make an Impact?</h2>
            <p className="text-lg text-muted-foreground">
              Join researchers, policymakers, and environmental advocates using data to drive Lahore toward a sustainable future
            </p>
            <div className="flex items-center justify-center gap-4 pt-4">
              <Button
                size="lg"
                onClick={() => setLocation("/signup")}
                data-testid="button-cta-signup"
              >
                Create Free Account
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => setLocation("/dashboard")}
                data-testid="button-cta-dashboard"
              >
                Explore Dashboard
              </Button>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Leaf className="h-4 w-4 text-primary" />
            <span className="font-semibold">Lahore Carbon Monitor</span>
          </div>
          <p>Environmental intelligence for a sustainable future</p>
        </div>
      </footer>
    </div>
  );
}
