import { z } from "zod";

// Regex SĐT giống hệt `phoneField` (lib/validations/auth.ts) - khác ở chỗ
// BẮT BUỘC ở đây (Backend OrderCreate.shipping_phone không cho rỗng), trong
// khi RegisterForm để optional - không tái dùng chung field vì ràng buộc
// required khác nhau.
export const checkoutSchema = z.object({
  shipping_name: z.string().trim().min(1, "Vui lòng nhập họ và tên người nhận."),
  shipping_phone: z
    .string()
    .min(1, "Vui lòng nhập số điện thoại.")
    .regex(/^0(3|5|7|8|9)\d{8}$/, "Số điện thoại không hợp lệ (VD: 0912345678)."),
  shipping_address: z
    .string()
    .trim()
    .min(1, "Vui lòng nhập địa chỉ giao hàng.")
    .max(500, "Địa chỉ tối đa 500 ký tự."),
  note: z.string().max(500, "Ghi chú tối đa 500 ký tự.").optional(),
});

export type CheckoutFormValues = z.infer<typeof checkoutSchema>;
