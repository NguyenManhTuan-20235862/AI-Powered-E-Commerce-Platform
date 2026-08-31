import { z } from "zod";

// Form thêm/sửa danh mục (CRUD Category Admin) - CỐ TÌNH KHÔNG có `slug`
// (Backend luôn tự sinh từ `name`, Admin không cần/không nên tự nhập tay -
// cùng quyết định UX đã áp dụng cho Product task 3.1.4, xem
// lib/validations/product.ts). `parent_id` là string rỗng "" = "Không có"
// (không cha) - map sang `undefined`/`null` tùy create hay update lúc submit
// (xem CategoryFormModal.tsx).
export const categoryFormSchema = z.object({
  name: z.string().trim().min(1, "Vui lòng nhập tên danh mục.").max(150, "Tên tối đa 150 ký tự."),
  description: z.string().max(500, "Mô tả tối đa 500 ký tự.").optional(),
  parent_id: z.string(),
});

export type CategoryFormValues = z.infer<typeof categoryFormSchema>;
