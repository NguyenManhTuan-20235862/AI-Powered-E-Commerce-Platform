import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

const baseStyles =
  "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";

const variantStyles: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "bg-brand-700 text-white hover:bg-brand-800",
  secondary: "bg-brand-100 text-brand-800 hover:bg-brand-200",
};

/** Component dùng chung - ví dụ quy ước cho các component trong components/ui. */
export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${className ?? ""}`}
      {...props}
    />
  );
}
