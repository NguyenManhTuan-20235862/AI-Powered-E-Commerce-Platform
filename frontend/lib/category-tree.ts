import type { Category } from "@/types/category";

/**
 * Dựng thứ tự CÂY (cha trước con, thụt lề theo `depth`) từ danh sách phẳng
 * `Category[]` (`GET /categories` không trả tree lồng nhau, chỉ `parent_id`
 * trơ) - dùng chung cho `CategoryTable.tsx` (hiển thị) VÀ `CategoryFormModal.tsx`
 * (dropdown chọn danh mục cha), thay cho sắp xếp alphabet phẳng cũ (không
 * phản ánh đúng phân cấp khi cây sâu ≥ 3 cấp - task "Hoàn thiện quản trị sản
 * phẩm, danh mục và kho").
 *
 * Mỗi node trả về kèm `ancestry` (toàn bộ tổ tiên từ gốc tới cha TRỰC TIẾP,
 * KHÔNG gồm chính nó) - đủ để hiện breadcrumb đầy đủ (VD "Điện tử > Điện
 * thoại") thay vì chỉ tên cha trực tiếp như bản cũ.
 *
 * Guard vòng lặp bằng `visited` (dữ liệu hợp lệ không thể có vòng lặp - Backend
 * đã chặn qua `category_service.would_create_cycle()` - nhưng phòng hờ dữ liệu
 * hỏng từ trước, tránh đệ quy vô hạn treo UI) - cùng tinh thần
 * `_MAX_PARENT_CHAIN_DEPTH` phía Backend.
 */
export interface CategoryTreeNode {
  category: Category;
  depth: number;
  ancestry: Category[];
}

export function buildCategoryTreeOrder(categories: Category[]): CategoryTreeNode[] {
  const byParent = new Map<number | null, Category[]>();
  for (const category of categories) {
    const key = category.parent_id ?? null;
    const siblings = byParent.get(key) ?? [];
    siblings.push(category);
    byParent.set(key, siblings);
  }
  for (const siblings of byParent.values()) {
    siblings.sort((a, b) => a.name.localeCompare(b.name, "vi"));
  }

  const result: CategoryTreeNode[] = [];
  const visited = new Set<number>();

  function visit(category: Category, depth: number, ancestry: Category[]) {
    if (visited.has(category.id)) return;
    visited.add(category.id);
    result.push({ category, depth, ancestry });
    const children = byParent.get(category.id) ?? [];
    for (const child of children) {
      visit(child, depth + 1, [...ancestry, category]);
    }
  }

  for (const root of byParent.get(null) ?? []) {
    visit(root, 0, []);
  }

  // Danh mục "mồ côi" (parent_id trỏ tới id không còn tồn tại trong danh sách -
  // KHÔNG nên xảy ra với dữ liệu hợp lệ vì FK RESTRICT, nhưng phòng hờ) - vẫn
  // hiện ở cuối thay vì biến mất hoàn toàn khỏi bảng.
  for (const category of categories) {
    if (!visited.has(category.id)) {
      visit(category, 0, []);
    }
  }

  return result;
}
