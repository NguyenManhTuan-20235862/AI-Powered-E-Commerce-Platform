import { z } from "zod";

const phoneField = z
  .string()
  .optional()
  .or(z.literal(""))
  .refine((v) => !v || /^0(3|5|7|8|9)\d{8}$/.test(v), {
    message: "Số điện thoại không hợp lệ (VD: 0912345678).",
  });

// Khớp UserUpdate (backend/app/schemas/user.py) - full_name/phone/address,
// KHÔNG có email/role (không đổi được qua trang hồ sơ).
export const profileUpdateSchema = z.object({
  full_name: z.string().trim().min(1, "Vui lòng nhập họ và tên.").min(2, "Họ và tên quá ngắn."),
  phone: phoneField,
  address: z.string().optional().or(z.literal("")),
});
export type ProfileUpdateFormValues = z.infer<typeof profileUpdateSchema>;

// Khớp ChangePasswordRequest (backend/app/schemas/user.py) - min_length=8 cho
// new_password, cùng ràng buộc RegisterForm (registerSchema, lib/validations/auth.ts)
// nhưng KHÔNG bắt buộc chữ hoa/số (Backend chỉ check min_length=8, không thêm
// ràng buộc nào khác cho đổi mật khẩu - giữ đúng khớp Backend, không tự thêm
// rule chặt hơn phía Frontend).
export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, "Vui lòng nhập mật khẩu hiện tại."),
    new_password: z.string().min(8, "Mật khẩu mới cần tối thiểu 8 ký tự."),
    confirm_password: z.string().min(1, "Vui lòng nhập lại mật khẩu mới."),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Mật khẩu xác nhận không khớp.",
    path: ["confirm_password"],
  });
export type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>;
