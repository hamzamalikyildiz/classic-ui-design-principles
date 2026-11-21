import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center justify-center rounded-md border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-border text-foreground",
        success: "border-transparent bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
        warning: "border-transparent bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
        destructive: "border-transparent bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200",
        // DELIBERATE DEFECT #3: 10px micro-badge triggers INFO shadcn-defaults
        micro: "border-transparent bg-amber-100 text-amber-900 text-[10px] px-1.5 py-0 leading-tight",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {children}
    </span>
  );
}

export { badgeVariants };
