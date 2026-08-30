"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { UserTable } from "@/components/admin/UserTable";
import { api } from "@/lib/axios";
import type { ApiResponse, PaginatedResponse } from "@/types/common";
import type { AdminUser, UserRole } from "@/types/user";

const SEARCH_DEBOUNCE_MS = 450;

/**
 * Client Component (port từ Stitch, task Quản lý người dùng Admin) - CSR,
 * cùng lý do `/admin/orders`/`/admin/products`: trang quản trị nội bộ, cần
 * tương tác ngay (search/filter/khóa-mở khóa không reload) hơn là cần SEO.
 * State filter (search/role/status/page) giữ ở `useState` THƯỜNG, KHÔNG
 * đồng bộ qua URL `searchParams` - tránh phải bọc `<Suspense>` (cùng quyết
 * định đã áp dụng cho `/admin/orders`, task 4.4.2).
 *
 * Gọi `GET /users` thật (`role`/`is_active`/`search`) - `is_active` gửi
 * "true"/"false" dạng string qua query param (FastAPI tự parse `bool`).
 */
export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<UserRole | "">("");
  const [isActive, setIsActive] = useState<"" | "true" | "false">("");

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: 10 };
      if (search) params.search = search;
      if (role) params.role = role;
      if (isActive) params.is_active = isActive;
      const { data } = await api.get<ApiResponse<PaginatedResponse<AdminUser>>>("/users", { params });
      setUsers(data.data.items);
      setTotalPages(data.data.total_pages);
    } catch {
      toast.error("Không tải được danh sách người dùng.");
    } finally {
      setIsLoading(false);
    }
  }, [page, search, role, isActive]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Debounce search - cùng pattern AdminOrdersPage/AdminProductsPage, luôn
  // quay về trang 1 khi đổi từ khóa.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput]);

  function handleRoleChange(value: UserRole | "") {
    setRole(value);
    setPage(1);
  }

  function handleStatusChange(value: "" | "true" | "false") {
    setIsActive(value);
    setPage(1);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl text-foreground">Quản lý người dùng</h1>
        <p className="mt-1 text-sm text-foreground-muted">Xem và quản lý tài khoản khách hàng.</p>
      </div>

      <UserTable
        users={users}
        isLoading={isLoading}
        search={searchInput}
        onSearchChange={setSearchInput}
        role={role}
        onRoleChange={handleRoleChange}
        isActive={isActive}
        onStatusChange={handleStatusChange}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        onChanged={fetchUsers}
      />
    </div>
  );
}
