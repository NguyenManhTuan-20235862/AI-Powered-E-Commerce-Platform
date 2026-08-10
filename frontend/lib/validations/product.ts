import { z } from "zod";

// Form thêm/sửa sản phẩm (task 4.4.1) - CỐ TÌNH KHÔNG có `stock_quantity`
// (đúng quyết định task 3.4.1 - `ProductUpdate` Backend không nhận field
// này qua PUT, xem docstring gốc) và KHÔNG có `slug` (Backend luôn tự sinh
// từ `name`, Admin không cần/không nên tự nhập tay - đơn giản hơn, tin
// tưởng auto-generate).
export const productFormSchema = z.object({
  name: z.string().trim().min(1, "Vui lòng nhập tên sản phẩm.").max(255, "Tên tối đa 255 ký tự."),
  category_id: z
    .string()
    .min(1, "Vui lòng chọn danh mục.")
    .refine((v) => Number(v) > 0, "Vui lòng chọn danh mục."),
  price: z
    .string()
    .min(1, "Vui lòng nhập giá.")
    .refine((v) => Number(v) > 0, "Giá phải lớn hơn 0."),
  description: z.string().max(2000, "Mô tả tối đa 2000 ký tự.").optional(),
  is_active: z.boolean(),
});

export type ProductFormValues = z.infer<typeof productFormSchema>;
