export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-50 px-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-sm">{children}</div>
    </div>
  );
}
