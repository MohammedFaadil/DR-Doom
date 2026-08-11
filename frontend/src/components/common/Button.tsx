import { ButtonHTMLAttributes, forwardRef } from "react";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md" | "lg";
}

const variants: Record<string, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 shadow-soft disabled:bg-brand-300 dark:disabled:bg-brand-900",
  secondary:
    "bg-ink-900 text-white hover:bg-ink-800 dark:bg-white dark:text-ink-900 dark:hover:bg-ink-100",
  outline:
    "border border-ink-200 dark:border-ink-700 text-ink-700 dark:text-ink-200 hover:bg-ink-100 dark:hover:bg-ink-800 bg-transparent",
  ghost: "text-ink-600 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800 bg-transparent",
  danger: "bg-red-600 text-white hover:bg-red-700",
};

const sizes: Record<string, string> = {
  sm: "text-xs px-3 py-1.5 rounded-lg gap-1.5",
  md: "text-sm px-4 py-2.5 rounded-xl gap-2",
  lg: "text-base px-6 py-3.5 rounded-2xl gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", className, type = "button", children, ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={twMerge(
        clsx(
          "inline-flex items-center justify-center font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-60 active:scale-[0.98]",
          variants[variant],
          sizes[size],
          className
        )
      )}
      {...props}
    >
      {children}
    </button>
  )
);
Button.displayName = "Button";
