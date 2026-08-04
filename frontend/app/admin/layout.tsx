import { Sidebar } from "@/components/layout/Sidebar";

// TODO (Thành viên B): bảo vệ layout này bằng middleware/useAuth (chỉ role="admin").
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
