import * as React from "react";
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
  title?: string;
  subtitle?: string;
  icon?: LucideIcon;
  breadcrumbItems?: { label: string; href?: string }[];
}

export function PageHeader({ breadcrumbItems }: PageHeaderProps) {
  if (!breadcrumbItems) return null;

  return (
    <div className="px-6 py-2.5 bg-gradient-to-r from-white/60 via-white/40 to-transparent dark:from-white/5 dark:via-white/[0.02] dark:to-transparent backdrop-blur-md border-b border-black/5 dark:border-white/5 z-20">
      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbItems.map((item, index) => (
            <React.Fragment key={item.label}>
              <BreadcrumbItem>
                {item.href ? (
                  <BreadcrumbLink asChild>
                    <Link href={item.href} className="cursor-pointer text-xs hover:text-emerald-500 transition-colors">
                      {item.label}
                    </Link>
                  </BreadcrumbLink>
                ) : (
                  <BreadcrumbPage className="text-xs font-medium text-emerald-600 dark:text-emerald-400">{item.label}</BreadcrumbPage>
                )}
              </BreadcrumbItem>
              {index < breadcrumbItems.length - 1 && <BreadcrumbSeparator />}
            </React.Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  );
}
