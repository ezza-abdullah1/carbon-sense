import * as React from "react";
import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Link } from "wouter";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  breadcrumbItems?: { label: string; href?: string }[];
}

export function PageHeader({ title, subtitle, icon: Icon, breadcrumbItems }: PageHeaderProps) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="relative px-8 py-6 border-b border-black/5 dark:border-white/5 bg-white/40 dark:bg-[#030303]/40 backdrop-blur-2xl z-20"
    >
      <div className="flex flex-col gap-4">
        {breadcrumbItems && (
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbItems.map((item, index) => (
                <React.Fragment key={item.label}>
                  <BreadcrumbItem>
                    {item.href ? (
                      <BreadcrumbLink asChild>
                        <Link href={item.href} className="cursor-pointer hover:text-emerald-500 transition-colors">
                          {item.label}
                        </Link>
                      </BreadcrumbLink>
                    ) : (
                      <BreadcrumbPage className="font-medium text-emerald-600 dark:text-emerald-400">{item.label}</BreadcrumbPage>
                    )}
                  </BreadcrumbItem>
                  {index < breadcrumbItems.length - 1 && <BreadcrumbSeparator />}
                </React.Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
        )}

        <div className="flex items-center gap-4">
          {Icon && (
            <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl bg-white dark:bg-white/5 border border-black/10 dark:border-white/10 shadow-xl text-emerald-600 dark:text-emerald-400 relative group overflow-hidden">
               <div className="absolute inset-0 bg-emerald-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
               <Icon className="h-6 w-6 relative z-10 transition-transform group-hover:scale-110" />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              {title}
            </h1>
            {subtitle && (
              <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                {subtitle}
              </p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
