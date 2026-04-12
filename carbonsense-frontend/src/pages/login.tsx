import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema, type LoginInput } from "@shared/schema";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { Leaf } from "lucide-react";
import { motion } from "framer-motion";

export default function Login() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const loginMutation = useMutation({
    mutationFn: async (data: LoginInput) => {
      const response = await apiRequest("POST", "/api/auth/login", data);
      return await response.json();
    },
    onSuccess: (data: { user: { id: string; email: string; name: string } }) => {
      toast({
        title: "Login successful",
        description: `Welcome back, ${data.user.name}!`,
      });
      localStorage.setItem("user", JSON.stringify(data.user));
      setLocation("/dashboard");
    },
    onError: (error: any) => {
      toast({
        title: "Login failed",
        description: error.message || "Invalid email or password",
        variant: "destructive",
      });
    },
  });

  const onSubmit = (data: LoginInput) => {
    loginMutation.mutate(data);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#fafafa] dark:bg-[#030303] relative overflow-hidden">
      {/* Animated Background Container */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <motion.div 
          animate={{ x: [0, 100, -50, 0], y: [0, -100, 50, 0], scale: [1, 1.2, 0.9, 1] }} transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute top-[10%] left-[30%] w-[50vw] h-[50vw] md:w-[30vw] md:h-[30vw] bg-emerald-400/20 dark:bg-emerald-600/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] md:blur-[120px] opacity-100" 
        />
        <motion.div 
          animate={{ x: [0, -80, 60, 0], y: [0, 80, -60, 0], scale: [1, 0.8, 1.1, 1] }} transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-[10%] right-[30%] w-[40vw] h-[40vw] md:w-[25vw] md:h-[25vw] bg-teal-300/20 dark:bg-teal-700/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] md:blur-[120px] opacity-100" 
        />
        <div className="absolute inset-0 overflow-hidden [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_100%)]">
          <motion.div 
            animate={{ y: [0, 40] }}
            transition={{ repeat: Infinity, duration: 2.5, ease: "linear" }}
            className="absolute -top-[40px] -left-0 -right-0 bottom-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PHBhdGggZD0iTTAgMGg0MHY0MEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDAuNWg0ME0wIDQwLjVoNDBNMC41IDB2NDBNNDAuNSAwdjQwIiBzdHJva2U9InJnYmEoMTUwLDE1MCwxNTAsMC4xKSIvPjwvc3ZnPg==')] dark:bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PHBhdGggZD0iTTAgMGg0MHY0MEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDAuNWg0ME0wIDQwLjVoNDBNMC41IDB2NDBNNDAuNSAwdjQwIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] opacity-100 dark:opacity-70 pointer-events-none" 
          />
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.8, type: "spring", bounce: 0.4 }}
        className="relative z-10 w-full max-w-md perspective-[1000px]"
      >
        <Card className="w-full bg-white/70 dark:bg-[#0a0a0a]/80 backdrop-blur-2xl border border-white/40 dark:border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.08)] dark:shadow-[0_8px_30px_rgb(16,185,129,0.1)] rounded-[2rem] overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none z-0" />
          <CardHeader className="space-y-2 relative z-10 pt-10">
            <motion.div 
              whileHover={{ rotate: 180 }}
              transition={{ duration: 0.5 }}
              className="flex items-center justify-center mb-4"
            >
              <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <Leaf className="h-7 w-7 text-white" />
              </div>
            </motion.div>
            <CardTitle className="text-3xl text-center font-extrabold tracking-tight text-slate-900 dark:text-white">Welcome Back</CardTitle>
            <CardDescription className="text-center text-slate-500 dark:text-slate-400 text-base">
              Sign in to access Lahore's carbon intelligence
            </CardDescription>
          </CardHeader>
          <CardContent className="relative z-10 pb-8 px-8">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-700 dark:text-slate-300 font-semibold">Email</FormLabel>
                      <FormControl>
                        <Input
                          className="h-12 rounded-xl bg-white/50 dark:bg-black/50 border-slate-200 dark:border-white/10 focus:ring-emerald-500 focus:border-emerald-500 transition-all text-base"
                          type="email"
                          placeholder="name@example.com"
                          data-testid="input-email"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-700 dark:text-slate-300 font-semibold">Password</FormLabel>
                      <FormControl>
                        <Input
                          className="h-12 rounded-xl bg-white/50 dark:bg-black/50 border-slate-200 dark:border-white/10 focus:ring-emerald-500 focus:border-emerald-500 transition-all text-base"
                          type="password"
                          placeholder="Enter your password"
                          data-testid="input-password"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    type="submit"
                    className="w-full h-12 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-bold text-lg border-0 shadow-lg shadow-emerald-500/25 transition-all"
                    disabled={loginMutation.isPending}
                    data-testid="button-login"
                  >
                    {loginMutation.isPending ? "Authenticating..." : "Sign In"}
                  </Button>
                </motion.div>
              </form>
            </Form>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4 relative z-10 pb-8 px-8 bg-slate-50/50 dark:bg-black/20 border-t border-slate-200 dark:border-white/5 pt-6">
            <div className="text-sm text-slate-500 dark:text-slate-400 text-center font-medium">
              Don't have an account?{" "}
              <button
                type="button"
                className="text-emerald-500 dark:text-emerald-400 font-bold hover:underline underline-offset-4 transition-all"
                onClick={() => setLocation("/signup")}
                data-testid="link-signup"
              >
                Create one now
              </button>
            </div>
            <Button
              variant="ghost"
              className="w-full h-10 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
              onClick={() => setLocation("/")}
              data-testid="button-back-home"
            >
              Back to Home
            </Button>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
}
