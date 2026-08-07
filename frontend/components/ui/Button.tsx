import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};

const baseStyles =
  "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-heading transition-colors disabled:cursor-not-allowed disabled:opacity-45";

const variantStyles: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary: "bg-primary text-background hover:bg-primary-hover",
  secondary: "bg-primary-100 text-primary-800 hover:bg-primary-300",
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
