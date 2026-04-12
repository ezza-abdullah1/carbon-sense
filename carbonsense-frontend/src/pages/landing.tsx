import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useLocation } from "wouter";
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import {
  Leaf, ArrowRight, Check, MapPin, Brain, BarChart3, Database,
  TrendingUp, Download, ShieldCheck, Zap
} from "lucide-react";
import { useEffect, useState } from "react";

const fadeUpParams = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

export default function Landing() {
  const [, setLocation] = useLocation();
  const [scrolled, setScrolled] = useState(false);
  const { scrollYProgress } = useScroll();
  const [imgError, setImgError] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const sectors = [
    { label: "Transport", color: "bg-indigo-500", shadow: "shadow-indigo-500/50" },
    { label: "Industry", color: "bg-rose-500", shadow: "shadow-rose-500/50" },
    { label: "Energy", color: "bg-amber-500", shadow: "shadow-amber-500/50" },
    { label: "Waste", color: "bg-orange-500", shadow: "shadow-orange-500/50" },
    { label: "Buildings", color: "bg-emerald-500", shadow: "shadow-emerald-500/50" },
  ];

  return (
    <div className="min-h-screen bg-[#fafafa] dark:bg-[#030303] text-slate-900 dark:text-slate-50 font-sans overflow-hidden selection:bg-emerald-200 dark:selection:bg-emerald-900 relative">
      {/* Global Animated Background Container */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {/* Glow Effects (Aurora) */}
        <motion.div 
          animate={{ x: [0, 100, -50, 0], y: [0, -100, 50, 0], scale: [1, 1.2, 0.9, 1] }} transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute top-[5%] left-[20%] w-[60vw] h-[60vw] md:w-[40vw] md:h-[40vw] bg-emerald-400/20 dark:bg-emerald-600/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] md:blur-[140px] opacity-100" 
        />
        <motion.div 
          animate={{ x: [0, -80, 60, 0], y: [0, 80, -60, 0], scale: [1, 0.8, 1.1, 1] }} transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          className="absolute top-[15%] right-[10%] w-[50vw] h-[50vw] md:w-[35vw] md:h-[35vw] bg-teal-300/20 dark:bg-teal-700/20 rounded-full mix-blend-multiply dark:mix-blend-screen filter blur-[100px] md:blur-[140px] opacity-100" 
        />
        
        {/* Layered Grid */}
        <div className="absolute inset-0 overflow-hidden [mask-image:radial-gradient(ellipse_at_top,black_40%,transparent_100%)]">
          <motion.div 
            animate={{ y: [0, 40] }}
            transition={{ repeat: Infinity, duration: 2.5, ease: "linear" }}
            className="absolute -top-[40px] -left-0 -right-0 bottom-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PHBhdGggZD0iTTAgMGg0MHY0MEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDAuNWg0ME0wIDQwLjVoNDBNMC41IDB2NDBNNDAuNSAwdjQwIiBzdHJva2U9InJnYmEoMTUwLDE1MCwxNTAsMC4xKSIvPjwvc3ZnPg==')] dark:bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PHBhdGggZD0iTTAgMGg0MHY0MEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDAuNWg0ME0wIDQwLjVoNDBNMC41IDB2NDBNNDAuNSAwdjQwIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] opacity-100 dark:opacity-70 pointer-events-none" 
          />
        </div>
      </div>
      
      {/* ============ NAVIGATION ============ */}
      <motion.nav 
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className={`fixed top-0 w-full z-50 transition-all duration-500 ${scrolled ? "bg-white/80 dark:bg-[#030303]/90 backdrop-blur-xl shadow-[0_4px_30px_rgba(0,0,0,0.03)] border-b border-white/20 dark:border-white/10" : "bg-transparent dark:bg-gradient-to-b dark:from-black/80 dark:to-transparent"}`}
      >
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer group" onClick={() => setLocation("/")}>
            <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:shadow-emerald-500/40 transition-all duration-300">
              <Leaf className="h-5 w-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight">Carbon<span className="text-emerald-500 dark:text-emerald-400 font-extrabold">Sense</span></span>
          </div>
          <div className="flex items-center gap-6">
            <ThemeToggle />
            <Button variant="ghost" className="hidden md:flex font-semibold hover:bg-slate-100 dark:hover:bg-white/5 text-slate-600 dark:text-slate-300 transition-colors" onClick={() => setLocation("/login")}>
              Sign In
            </Button>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button onClick={() => setLocation("/signup")} className="bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-slate-100 text-white dark:text-black font-semibold border-0 rounded-full px-6 h-11 transition-colors shadow-xl shadow-black/10 dark:shadow-white/10">
                Get Started
              </Button>
            </motion.div>
          </div>
        </div>
      </motion.nav>

      {/* ============ HERO SECTION ============ */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-32 px-6 min-h-screen flex items-center justify-center overflow-hidden">
        
        {/* Removed redundant aurora to fix z-index masking */}

        <div className="max-w-5xl mx-auto text-center relative z-10 flex flex-col items-center">
          
          <motion.div 
            initial={{ opacity: 0, scale: 0.8, y: 20 }} 
            animate={{ opacity: 1, scale: 1, y: 0 }} 
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="mb-8"
          >
            <div className="inline-flex items-center justify-center p-[1px] rounded-full bg-gradient-to-r from-emerald-500/50 via-teal-400/50 to-blue-500/50 overflow-hidden shadow-lg shadow-emerald-500/10">
              <div className="px-4 py-1.5 rounded-full bg-white dark:bg-black/80 backdrop-blur-xl flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-sm font-semibold tracking-wide text-slate-800 dark:text-slate-200">
                  Next-Gen Carbon Intelligence
                </span>
              </div>
            </div>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="text-6xl md:text-8xl font-extrabold tracking-tighter mb-6 text-slate-900 dark:text-white leading-[1.05]"
          >
            Monitor Emissions <br className="hidden md:block"/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-500 animate-gradient-x">
              With Precision
            </span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
            className="text-xl md:text-2xl text-slate-600 dark:text-slate-400 mb-12 max-w-3xl mx-auto leading-relaxed font-light"
          >
            The world's most advanced environmental AI. Turning global satellite data into actionable localized insights for a sustainable zero-carbon future.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5, ease: "easeOut" }}
            className="flex flex-col sm:flex-row gap-5 mb-20 w-full sm:w-auto"
          >
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} className="w-full sm:w-auto">
              <Button size="lg" onClick={() => setLocation("/dashboard")} className="w-full sm:w-auto bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white border-0 shadow-2xl shadow-emerald-500/30 rounded-full px-10 h-16 text-lg font-bold group transition-all">
                Explore The Map
                <ArrowRight className="ml-3 h-5 w-5 group-hover:translate-x-1.5 transition-transform" />
              </Button>
            </motion.div>
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} className="w-full sm:w-auto">
              <Button size="lg" variant="outline" onClick={() => setLocation("/signup")} className="w-full sm:w-auto bg-white/50 hover:bg-white dark:bg-white/5 dark:hover:bg-white/10 border-slate-200 dark:border-white/10 rounded-full px-10 h-16 text-lg font-bold backdrop-blur-xl shadow-lg transition-all text-slate-900 dark:text-white">
                Request API Access
              </Button>
            </motion.div>
          </motion.div>

          {/* Sector tags - Floating Modern Pills */}
          <motion.div 
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="flex flex-wrap justify-center gap-4"
          >
            {sectors.map((sector, i) => (
              <motion.div 
                key={sector.label}
                initial={{ opacity: 0, scale: 0.5, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ delay: 0.6 + (i * 0.1), type: "spring", stiffness: 200 }}
                whileHover={{ y: -5, scale: 1.05 }}
                className="group relative cursor-default"
              >
                {/* Glow effect behind pill */}
                <div className={`absolute inset-0 ${sector.color} opacity-0 group-hover:opacity-30 blur-xl transition-opacity duration-300 rounded-full`} />
                <div className="relative inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-white/70 dark:bg-black/50 backdrop-blur-md border border-slate-200 dark:border-white/10 text-sm font-semibold text-slate-800 dark:text-slate-200 shadow-xl shadow-black/5">
                  <span className={`h-3 w-3 rounded-full ${sector.color} ${sector.shadow} shadow-md`} />
                  {sector.label}
                </div>
              </motion.div>
            ))}
          </motion.div>

        </div>
      </section>

      {/* ============ PREMIUM BENTO GRID (How it Works) ============ */}
      <section className="py-24 px-6 relative z-10">
        <div className="max-w-7xl mx-auto">
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            className="text-center mb-20"
          >
            <h2 className="text-4xl md:text-5xl font-extrabold mb-5 tracking-tight text-slate-900 dark:text-white">The Intelligence Engine</h2>
            <p className="text-xl text-slate-500 dark:text-slate-400 max-w-2xl mx-auto font-light">
              Transforming raw, unstructured satellite telemetry into highly precise, actionable climate intelligence.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Card 1 */}
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              whileHover={{ y: -10 }}
              transition={{ duration: 0.6, type: "spring", stiffness: 100 }}
              className="relative group rounded-[2.5rem] bg-gradient-to-b from-slate-100 to-white dark:from-slate-900 dark:to-black p-1 shadow-2xl shadow-blue-500/5 dark:shadow-blue-500/10 overflow-hidden"
            >
              {/* Animated Gradient Border Layer */}
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/30 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              
              <div className="relative h-full bg-white dark:bg-[#0a0a0a] rounded-[2.4rem] p-10 border border-transparent dark:border-white/5 flex flex-col items-start overflow-hidden">
                <div className="absolute top-0 right-0 -mr-10 -mt-10 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-all duration-500" />
                
                <div className="h-16 w-16 px-0 flex items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/20 text-blue-600 dark:text-blue-400 mb-8 shadow-inner">
                  <Database className="h-8 w-8" />
                </div>
                
                <h3 className="text-2xl font-bold mb-4 text-slate-900 dark:text-white tracking-tight">1. Ingest Data</h3>
                <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-lg font-light flex-grow">
                  We hook directly into Climate Trace, aggregating petabytes of satellite imagery, remote sensing, and ground-truth telemetry daily.
                </p>
              </div>
            </motion.div>

            {/* Card 2 (Accented/Primary) */}
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              whileHover={{ y: -10, scale: 1.02 }}
              transition={{ duration: 0.6, delay: 0.1, type: "spring", stiffness: 100 }}
              className="relative group rounded-[2.5rem] bg-gradient-to-b from-emerald-400 via-teal-500 to-emerald-600 p-[2px] shadow-2xl shadow-emerald-500/20 md:-mt-8 md:mb-8"
            >
              <div className="relative h-full bg-white dark:bg-[#050505] rounded-[2.4rem] p-10 flex flex-col items-start overflow-hidden backdrop-blur-3xl">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent z-0" />
                <div className="absolute bottom-0 left-0 w-60 h-60 bg-emerald-500/20 rounded-full blur-[80px] group-hover:blur-[100px] transition-all duration-500 z-0" />
                
                <div className="relative z-10 h-16 w-16 flex items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 text-white mb-8 shadow-lg shadow-emerald-500/30">
                  <Brain className="h-8 w-8" />
                </div>
                
                <h3 className="text-2xl font-bold mb-4 text-slate-900 dark:text-white tracking-tight relative z-10">2. ML Analysis</h3>
                <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-lg font-light flex-grow relative z-10">
                  Proprietary Hybrid XGBoost + Prophet architecture parses the noise, identifying hidden patterns and emitting highly accurate 12-month forecasts.
                </p>
              </div>
            </motion.div>

            {/* Card 3 */}
            <motion.div 
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              whileHover={{ y: -10 }}
              transition={{ duration: 0.6, delay: 0.2, type: "spring", stiffness: 100 }}
              className="relative group rounded-[2.5rem] bg-gradient-to-b from-slate-100 to-white dark:from-slate-900 dark:to-black p-1 shadow-2xl shadow-purple-500/5 dark:shadow-purple-500/10 overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/30 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              
              <div className="relative h-full bg-white dark:bg-[#0a0a0a] rounded-[2.4rem] p-10 border border-transparent dark:border-white/5 flex flex-col items-start overflow-hidden">
                <div className="absolute top-0 right-0 -mr-10 -mt-10 w-40 h-40 bg-purple-500/10 rounded-full blur-3xl group-hover:bg-purple-500/20 transition-all duration-500" />
                
                <div className="h-16 w-16 px-0 flex items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500/20 to-purple-600/10 border border-purple-500/20 text-purple-600 dark:text-purple-400 mb-8 shadow-inner">
                  <BarChart3 className="h-8 w-8" />
                </div>
                
                <h3 className="text-2xl font-bold mb-4 text-slate-900 dark:text-white tracking-tight">3. Visualize & Act</h3>
                <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-lg font-light flex-grow">
                  Insights are surfaced through high-performance dashboards, enabling instant policy-simulation and data-backed decision making.
                </p>
              </div>
            </motion.div>

          </div>
        </div>
      </section>

      {/* ============ STATS SECTION (MODERN FLOAT) ============ */}
      <section className="py-16 px-6 relative z-10 z-20">
        <div className="max-w-7xl mx-auto">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, type: "spring" }}
            className="rounded-[3rem] bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 p-12 overflow-hidden relative shadow-2xl"
          >
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PHBhdGggZD0iTTAgMGg0MHY0MEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDAuNWg0ME0wIDQwLjVoNDBNMC41IDB2NDBNNDAuNSAwdjQwIiBzdHJva2U9InJnYmEoMTUwLDE1MCwxNTAsMC4wNSkiLz48L3N2Zz4=')] dark:bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+PHBhdGggZD0iTTAgMGg0MHY0MEgweiIgZmlsbD0ibm9uZSIvPjxwYXRoIGQ9Ik0wIDAuNWg0ME0wIDQwLjVoNDBNMC41IDB2NDBNNDAuNSAwdjQwIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')] [mask-image:radial-gradient(ellipse_at_center,black_50%,transparent_100%)] opacity-30" />
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-12 relative z-10 divide-x-0 md:divide-x divide-slate-200 dark:divide-white/10">
              {[
                { number: "50+", label: "Areas Mapped" },
                { number: "5", label: "Core Sectors" },
                { number: "3+", label: "Years Tracking" },
                { number: "94%", label: "Algorithm Accuracy" },
              ].map((stat, i) => (
                <motion.div 
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.6 }}
                  className="flex flex-col items-center justify-center text-center group"
                >
                  <div className="text-5xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-b from-slate-900 to-slate-500 dark:from-white dark:to-slate-400 mb-3 tracking-tighter group-hover:scale-110 transition-transform duration-300">
                    {stat.number}
                  </div>
                  <div className="text-sm text-slate-400 font-bold tracking-[0.2em] uppercase">
                    {stat.label}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ============ FEATURE SHOWCASE (HOVER CARDS) ============ */}
      <section className="py-24 px-6 relative">
        <div className="w-full max-w-[90rem] mx-auto xl:px-12">
          
          <div className="space-y-24">
            {/* Feature 1 */}
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <motion.div 
                initial={{ opacity: 0, x: -50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.8 }}
                className="order-2 lg:order-1 relative"
              >
                <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-sm font-bold tracking-wide">
                  <MapPin className="h-4 w-4" /> Spatial Analytics
                </div>
                <h3 className="text-4xl md:text-5xl font-extrabold mb-6 tracking-tight text-slate-900 dark:text-white leading-[1.1]">
                  High-Fidelity <br/>Emission Mapping
                </h3>
                <p className="text-xl text-slate-600 dark:text-slate-400 mb-10 leading-relaxed font-light">
                  Interact with real-time geographical data. Our platform breaks down the massive carbon footprint of Lahore into digestible, neighborhood-level telemetry.
                </p>
                <ul className="space-y-5">
                  {["50+ distinctly monitored zones", "Sector-wise geographical filtering", "Heatmap intensity visualizations"].map((item, i) => (
                    <motion.li 
                      key={i} 
                      whileHover={{ x: 10 }}
                      className="flex items-center gap-4 text-slate-800 dark:text-slate-300 font-medium text-lg"
                    >
                      <div className="h-8 w-8 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                        <Check className="h-4 w-4 text-emerald-500" />
                      </div>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
              <motion.div 
                initial={{ opacity: 0, scale: 0.9, rotateY: -15, rotateX: 10 }}
                whileInView={{ opacity: 1, scale: 1, rotateY: 0, rotateX: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1.2, type: "spring", bounce: 0.4 }}
                className="order-1 lg:order-2 perspective-[2000px]"
              >
                <div className="relative rounded-[2.5rem] bg-gradient-to-tr from-slate-200 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-2 shadow-2xl shadow-emerald-500/10 transform-style-3d hover:scale-[1.03] transition-transform duration-700">
                   <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-[2.8rem] opacity-30 blur-2xl z-[-1]" />
                   {!imgError['map'] ? (
                     <img src="/images/feature-map.png" alt="Map Interface" className="h-72 lg:h-[350px] object-cover rounded-[2.2rem] w-full border border-white/20 dark:border-white/10 relative z-10" onError={() => setImgError(prev => ({...prev, map: true}))} />
                   ) : (
                     <div className="h-72 lg:h-[350px] w-full rounded-[2.2rem] bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 flex items-center justify-center relative z-10 box-shadow-2xl">
                       <div className="text-slate-500 flex flex-col items-center"><MapPin className="h-12 w-12 mb-4 opacity-50"/><span className="font-semibold tracking-widest text-sm uppercase">Map Interface</span></div>
                     </div>
                   )}
                </div>
              </motion.div>
            </div>

            {/* Feature 2 */}
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <motion.div 
                initial={{ opacity: 0, scale: 0.9, rotateY: 15, rotateX: 10 }}
                whileInView={{ opacity: 1, scale: 1, rotateY: 0, rotateX: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1.2, type: "spring", bounce: 0.4 }}
                className="perspective-[2000px]"
              >
                <div className="relative rounded-[2.5rem] bg-gradient-to-tr from-slate-200 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-2 shadow-2xl shadow-blue-500/10 transform-style-3d hover:scale-[1.03] transition-transform duration-700">
                   <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-[2.8rem] opacity-30 blur-2xl z-[-1]" />
                   {!imgError['forecast'] ? (
                     <img src="/images/feature-forecast.png" alt="Forecasting Interface" className="h-72 lg:h-[350px] object-cover rounded-[2.2rem] w-full border border-white/20 dark:border-white/10 relative z-10" onError={() => setImgError(prev => ({...prev, forecast: true}))} />
                   ) : (
                     <div className="h-72 lg:h-[350px] w-full rounded-[2.2rem] bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 flex items-center justify-center relative z-10">
                       <div className="text-slate-500 flex flex-col items-center"><Brain className="h-12 w-12 mb-4 opacity-50"/><span className="font-semibold tracking-widest text-sm uppercase">Forecasting Interface</span></div>
                     </div>
                   )}
                </div>
              </motion.div>
              <motion.div 
                initial={{ opacity: 0, x: 50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.8 }}
                className="relative"
              >
                <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400 text-sm font-bold tracking-wide">
                  <Brain className="h-4 w-4" /> Predictive Modeling
                </div>
                <h3 className="text-4xl md:text-5xl font-extrabold mb-6 tracking-tight text-slate-900 dark:text-white leading-[1.1]">
                  Simulate The Future
                </h3>
                <p className="text-xl text-slate-600 dark:text-slate-400 mb-10 leading-relaxed font-light">
                  Don't just react to data—anticipate it. Our hybrid neural network architectures cast precisely 12 months into the future, enabling proactive policy interventions.
                </p>
                <ul className="space-y-5">
                  {["XGBoost + Prophet hybrid architecture", "94.6% predictive validation accuracy", "Interactive forward-casting scenarios"].map((item, i) => (
                    <motion.li 
                      key={i} 
                      whileHover={{ x: 10 }}
                      className="flex items-center gap-4 text-slate-800 dark:text-slate-300 font-medium text-lg"
                    >
                      <div className="h-8 w-8 rounded-full bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                        <Check className="h-4 w-4 text-blue-500" />
                      </div>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
            </div>

            {/* Feature 3: Historical Trends & Monthly Patterns */}
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <motion.div 
                initial={{ opacity: 0, x: -50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.8 }}
                className="order-2 lg:order-1 relative"
              >
                <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-sm font-bold tracking-wide">
                  <TrendingUp className="h-4 w-4" /> Historical Analysis
                </div>
                <h3 className="text-4xl md:text-5xl font-extrabold mb-6 tracking-tight text-slate-900 dark:text-white leading-[1.1]">
                  Deep Historical <br/>Trends
                </h3>
                <p className="text-xl text-slate-600 dark:text-slate-400 mb-10 leading-relaxed font-light">
                  Analyze past emission patterns across more than 535 independent sources. Interrogate sector distributions and uncover hidden seasonal monthly patterns stretching backward to 2021.
                </p>
                <ul className="space-y-5">
                  {["Top emission sources tracking", "Monthly cyclical pattern detection", "Aggregated sector distributions"].map((item, i) => (
                    <motion.li 
                      key={i} 
                      whileHover={{ x: 10 }}
                      className="flex items-center gap-4 text-slate-800 dark:text-slate-300 font-medium text-lg"
                    >
                      <div className="h-8 w-8 rounded-full bg-rose-500/10 flex items-center justify-center border border-rose-500/20">
                        <Check className="h-4 w-4 text-rose-500" />
                      </div>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
              <motion.div 
                initial={{ opacity: 0, scale: 0.9, rotateY: -15, rotateX: 10 }}
                whileInView={{ opacity: 1, scale: 1, rotateY: 0, rotateX: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1.2, type: "spring", bounce: 0.4 }}
                className="order-1 lg:order-2 perspective-[2000px]"
              >
                <div className="relative rounded-[2.5rem] bg-gradient-to-tr from-slate-200 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-2 shadow-2xl shadow-rose-500/10 transform-style-3d hover:scale-[1.03] transition-transform duration-700">
                   <div className="absolute -inset-1 bg-gradient-to-r from-rose-500 to-orange-500 rounded-[2.8rem] opacity-30 blur-2xl z-[-1]" />
                   {!imgError['historical'] ? (
                     <img src="/images/historical-trends.png" alt="Historical Trends Interface" className="h-72 lg:h-[350px] object-cover rounded-[2.2rem] w-full border border-white/20 dark:border-white/10 relative z-10" onError={() => setImgError(prev => ({...prev, historical: true}))} />
                   ) : (
                     <div className="h-72 lg:h-[350px] w-full rounded-[2.2rem] bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 flex flex-col items-center justify-center relative z-10 box-shadow-2xl overflow-hidden p-6 gap-4">
                       {/* Mock graph UI elements for UI aesthetic */}
                       <div className="w-full flex justify-between items-end h-1/2 border-b border-slate-200 dark:border-white/10 pb-4 px-4 gap-2">
                           {[60, 80, 45, 90, 65, 75].map((h, i) => (
                             <motion.div key={i} className="w-1/6 bg-rose-500/80 rounded-t-lg" initial={{ height: 0 }} whileInView={{ height: `${h}%` }} transition={{ delay: 0.2 + (i * 0.1), duration: 0.6 }} />
                           ))}
                       </div>
                       <div className="text-slate-500 flex flex-col items-center mt-2"><TrendingUp className="h-8 w-8 mb-2 opacity-50"/><span className="font-semibold tracking-widest text-sm uppercase">Historical Patterns</span></div>
                     </div>
                   )}
                </div>
              </motion.div>
            </div>

            {/* Feature 4: Historical vs Predicted Synthesis */}
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <motion.div 
                initial={{ opacity: 0, scale: 0.9, rotateY: 15, rotateX: 10 }}
                whileInView={{ opacity: 1, scale: 1, rotateY: 0, rotateX: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1.2, type: "spring", bounce: 0.4 }}
                className="perspective-[2000px]"
              >
                <div className="relative rounded-[2.5rem] bg-gradient-to-tr from-slate-200 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-2 shadow-2xl shadow-purple-500/10 transform-style-3d hover:scale-[1.03] transition-transform duration-700">
                   <div className="absolute -inset-1 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-[2.8rem] opacity-30 blur-2xl z-[-1]" />
                   {!imgError['synthesis'] ? (
                     <img src="/images/forecast-analysis.png" alt="Forecast Synthesis Interface" className="h-72 lg:h-[350px] object-cover rounded-[2.2rem] w-full border border-white/20 dark:border-white/10 relative z-10" onError={() => setImgError(prev => ({...prev, synthesis: true}))} />
                   ) : (
                     <div className="h-72 lg:h-[350px] w-full rounded-[2.2rem] bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 flex items-center justify-center relative z-10 overflow-hidden p-6">
                       <div className="w-full h-full relative flex flex-col items-center justify-center">
                          {/* Mock predictive lines */}
                          <svg viewBox="0 0 100 50" className="absolute inset-0 w-full h-full text-indigo-500 stroke-current z-0" preserveAspectRatio="none">
                            <motion.path d="M0,40 Q25,35 50,25 T100,10" fill="none" strokeWidth="2" initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} transition={{ duration: 1.5 }} />
                            <circle cx="50" cy="25" r="1.5" className="fill-purple-400" />
                            <circle cx="75" cy="15" r="1.5" className="fill-purple-400 animate-pulse" />
                            <circle cx="100" cy="10" r="1.5" className="fill-yellow-400 animate-pulse" />
                          </svg>
                          <div className="relative z-10 flex items-center justify-center text-slate-500 flex-col"><BarChart3 className="h-8 w-8 mb-2 opacity-50"/><span className="font-semibold tracking-widest text-sm uppercase">Forecast Synthesis</span></div>
                       </div>
                     </div>
                   )}
                </div>
              </motion.div>
              <motion.div 
                initial={{ opacity: 0, x: 50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.8 }}
                className="relative"
              >
                <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-600 dark:text-purple-400 text-sm font-bold tracking-wide">
                  <BarChart3 className="h-4 w-4" /> Forecast Synthesis
                </div>
                <h3 className="text-4xl md:text-5xl font-extrabold mb-6 tracking-tight text-slate-900 dark:text-white leading-[1.1]">
                  Historical vs <br/>Predicted Convergence
                </h3>
                <p className="text-xl text-slate-600 dark:text-slate-400 mb-10 leading-relaxed font-light">
                  Visually trace the exact trajectory of climate interventions. We seamlessly bridge actual historical records directly into ML-driven future predictions.
                </p>
                <ul className="space-y-5">
                  {["Continuous 5-year macro timelines", "95% statistical confidence intervals", "Sector-by-sector comparative graphing"].map((item, i) => (
                    <motion.li 
                      key={i} 
                      whileHover={{ x: 10 }}
                      className="flex items-center gap-4 text-slate-800 dark:text-slate-300 font-medium text-lg"
                    >
                      <div className="h-8 w-8 rounded-full bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
                        <Check className="h-4 w-4 text-purple-500" />
                      </div>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
            </div>

            {/* Feature 5 */}
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <motion.div 
                initial={{ opacity: 0, x: -50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.8 }}
                className="order-2 lg:order-1 relative"
              >
                <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-600 dark:text-orange-400 text-sm font-bold tracking-wide">
                  <Download className="h-4 w-4" /> Export & Integrations
                </div>
                <h3 className="text-4xl md:text-5xl font-extrabold mb-6 tracking-tight text-slate-900 dark:text-white leading-[1.1]">
                  Data Export & <br/>API Hooks
                </h3>
                <p className="text-xl text-slate-600 dark:text-slate-400 mb-10 leading-relaxed font-light">
                  Extract raw intelligence packages seamlessly. Build directly on top of our data foundation with highly performant server-side RestAPI webhooks and real-time streaming drops.
                </p>
                <ul className="space-y-5">
                  {["Raw historical CSV/JSON packages", "Restful API connectivity", "Zero-latency payload delivery"].map((item, i) => (
                    <motion.li 
                      key={i} 
                      whileHover={{ x: 10 }}
                      className="flex items-center gap-4 text-slate-800 dark:text-slate-300 font-medium text-lg"
                    >
                      <div className="h-8 w-8 rounded-full bg-orange-500/10 flex items-center justify-center border border-orange-500/20">
                        <Check className="h-4 w-4 text-orange-500" />
                      </div>
                      {item}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
              <motion.div 
                initial={{ opacity: 0, scale: 0.9, rotateY: -15, rotateX: 10 }}
                whileInView={{ opacity: 1, scale: 1, rotateY: 0, rotateX: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 1.2, type: "spring", bounce: 0.4 }}
                className="order-1 lg:order-2 perspective-[2000px]"
              >
                <div className="relative rounded-[2.5rem] bg-gradient-to-tr from-slate-200 to-slate-100 dark:from-slate-800 dark:to-slate-900 p-2 shadow-2xl shadow-orange-500/10 transform-style-3d hover:scale-[1.03] transition-transform duration-700">
                   <div className="absolute -inset-1 bg-gradient-to-r from-orange-500 to-amber-500 rounded-[2.8rem] opacity-30 blur-2xl z-[-1]" />
                   {!imgError['export'] ? (
                     <img src="/images/export-gateway.png" alt="Export Interface" className="h-72 lg:h-[350px] object-cover rounded-[2.2rem] w-full border border-white/20 dark:border-white/10 relative z-10" onError={() => setImgError(prev => ({...prev, export: true}))} />
                   ) : (
                     <div className="h-72 lg:h-[350px] w-full rounded-[2.2rem] bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 relative z-10 flex flex-col items-center justify-center overflow-hidden">
                       {/* Animated Data Stream */}
                       <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none opacity-30">
                         <motion.div 
                           initial={{ y: -100, opacity: 0 }} 
                           animate={{ y: 200, opacity: [0, 1, 0] }} 
                           transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                           className="w-1 h-32 bg-gradient-to-b from-transparent via-orange-500 to-transparent blur-sm"
                         />
                         <motion.div 
                           initial={{ y: -150, opacity: 0 }} 
                           animate={{ y: 200, opacity: [0, 1, 0] }} 
                           transition={{ repeat: Infinity, duration: 2, delay: 0.5, ease: "linear" }}
                           className="absolute left-1/3 w-1 h-20 bg-gradient-to-b from-transparent via-amber-500 to-transparent blur-sm"
                         />
                         <motion.div 
                           initial={{ y: -50, opacity: 0 }} 
                           animate={{ y: 200, opacity: [0, 1, 0] }} 
                           transition={{ repeat: Infinity, duration: 1.8, delay: 1, ease: "linear" }}
                           className="absolute right-1/3 w-1 h-24 bg-gradient-to-b from-transparent via-red-500 to-transparent blur-sm"
                         />
                       </div>
                       <motion.div 
                          animate={{ y: [0, -5, 0] }}
                          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                       >
                         <Download className="h-16 w-16 text-orange-500/80 mb-4 z-10 drop-shadow-[0_0_15px_rgba(249,115,22,0.3)]"/>
                       </motion.div>
                       <span className="font-semibold tracking-widest text-slate-400 text-sm uppercase z-10">Secure Export Gateway</span>
                     </div>
                   )}
                </div>
              </motion.div>
            </div>

          </div>
        </div>
      </section>

      {/* ============ CTA SECTION (GLASSMORPHISM) ============ */}
      <section className="py-20 px-6 relative mt-10">
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, type: "spring", bounce: 0.3 }}
            className="relative rounded-[3rem] p-12 md:p-24 overflow-hidden shadow-2xl bg-white dark:bg-[#0a0a0a] border border-slate-200 dark:border-white/10"
          >
            {/* Animated Inner Glowing Gradients */}
            <motion.div 
              animate={{ rotate: 360 }}
              transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
              className="absolute -top-[50%] -left-[50%] w-[200%] h-[200%] bg-[conic-gradient(from_0deg,transparent,rgba(16,185,129,0.1),rgba(59,130,246,0.1),transparent)] dark:bg-[conic-gradient(from_0deg,transparent,rgba(16,185,129,0.2),rgba(59,130,246,0.2),transparent)] z-0" 
            />
            
            <div className="relative z-10">
              <h2 className="text-5xl md:text-6xl font-extrabold mb-8 tracking-tighter text-slate-900 dark:text-white">
                Begin Tracking Today
              </h2>
              <p className="text-xl text-slate-600 dark:text-slate-400 mb-12 max-w-2xl mx-auto font-light leading-relaxed">
                Join the ecosystem of policymakers, scientists, and citizens powering the environmental intelligence revolution.
              </p>
              <div className="flex flex-col sm:flex-row justify-center gap-4">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button size="lg" onClick={() => setLocation("/signup")} className="bg-emerald-500 hover:bg-emerald-400 text-white font-bold border-0 rounded-full px-12 h-16 w-full sm:w-auto shadow-xl shadow-emerald-500/30 text-lg transition-all">
                    Create Free Account
                  </Button>
                </motion.div>
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button size="lg" variant="outline" onClick={() => setLocation("/dashboard")} className="bg-white/10 hover:bg-slate-100 dark:hover:bg-white/5 text-slate-900 dark:text-white border-slate-300 dark:border-white/20 rounded-full px-12 h-16 w-full sm:w-auto shadow-sm text-lg font-bold backdrop-blur-xl transition-all">
                    Explore Dashboard
                  </Button>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ============ ELITE FOOTER ============ */}
      <footer className="py-16 px-6 relative z-10 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 transition-colors duration-300">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row justify-between items-start gap-12 border-b border-slate-200 dark:border-slate-800 pb-12 mb-8 transition-colors duration-300">
            <div className="flex flex-col gap-6 max-w-sm">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                  <Leaf className="h-5 w-5 text-white" />
                </div>
                <span className="font-bold text-2xl tracking-tight text-slate-900 dark:text-white transition-colors duration-300">Carbon<span className="text-emerald-500">Sense</span></span>
              </div>
              <p className="text-base text-slate-500 dark:text-slate-400 leading-relaxed font-light transition-colors duration-300">
                The world's most advanced environmental AI. Turning global satellite data into actionable localized insights for a sustainable zero-carbon future.
              </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-12 lg:gap-24 w-full lg:w-auto">
              {[
                { title: "Platform", links: ["Intelligence Engine", "Data Export API", "Predictive Models", "Case Studies"] },
                { title: "Resources", links: ["Documentation", "Blog", "Community", "Support Centre"] },
                { title: "Company", links: ["About Us", "Media Kit", "Careers", "Contact Sales"] }
              ].map((column) => (
                <div key={column.title} className="flex flex-col gap-4">
                  <h4 className="text-slate-900 dark:text-white font-semibold text-lg mb-2 transition-colors duration-300">{column.title}</h4>
                  {column.links.map((link) => (
                    <a key={link} href="#" className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors">
                      {link}
                    </a>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="text-sm text-slate-500 font-medium">
              © {new Date().getFullYear()} CarbonSense Inc. All rights reserved.
            </p>
            <div className="flex gap-8">
               {['Twitter', 'GitHub', 'LinkedIn'].map((link) => (
                  <a key={link} href="#" className="text-sm text-slate-500 font-medium hover:text-slate-800 dark:hover:text-slate-300 transition-colors">
                    {link}
                  </a>
                ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
