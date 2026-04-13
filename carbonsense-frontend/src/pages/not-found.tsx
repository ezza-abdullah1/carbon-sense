import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import { useLocation } from "wouter";

export default function NotFound() {
  const [, setLocation] = useLocation();

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#fafafa] dark:bg-[#030303]">
      <Card className="w-full max-w-md mx-4 bg-white/70 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border border-white/40 dark:border-white/10 shadow-xl">
        <CardContent className="pt-6">
          <div className="flex mb-4 gap-2">
            <AlertCircle className="h-8 w-8 text-red-500" />
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">404 Page Not Found</h1>
          </div>

          <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">
            The page you're looking for doesn't exist or has been moved.
          </p>

          <div className="mt-6 flex gap-3">
            <Button
              onClick={() => setLocation("/")}
              className="bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white border-0 shadow-lg shadow-emerald-500/25"
            >
              Back to Home
            </Button>
            <Button
              variant="outline"
              onClick={() => setLocation("/dashboard")}
              className="border-slate-200 dark:border-white/10"
            >
              Go to Dashboard
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
