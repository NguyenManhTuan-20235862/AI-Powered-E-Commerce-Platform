import { z } from "zod";

const emailField = z
  .string()
  .min(1, "Vui lòng nhập email.")
  .email("Email không đúng định dạng.");

const phoneField = z
  .string()
  .optional()
  .or(z.literal(""))
  .refine((v) => !v || /^0(3|5|7|8|9)\d{8}$/.test(v), {
    message: "Số điện thoại không hợp lệ (VD: 0912345678).",
  });

export const loginSchema = z.object({
  email: emailField,
  password: z.string().min(1, "Vui lòng nhập mật khẩu."),
  remember: z.boolean().optional(),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(1, "Vui lòng nhập họ và tên.")
      .min(2, "Họ và tên quá ngắn."),
    email: emailField,
    phone: phoneField,
    password: z
      .string()
      .min(8, "Mật khẩu cần tối thiểu 8 ký tự, có chữ hoa và số.")
      .regex(/[A-Z]/, "Mật khẩu cần tối thiểu 8 ký tự, có chữ hoa và số.")
      .regex(/\d/, "Mật khẩu cần tối thiểu 8 ký tự, có chữ hoa và số."),
    confirmPassword: z.string().min(1, "Vui lòng nhập lại mật khẩu."),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Mật khẩu xác nhận không khớp.",
    path: ["confirmPassword"],
  });
export type RegisterFormValues = z.infer<typeof registerSchema>;
