export function Footer() {
  return (
    <footer className="border-t border-brand-100 bg-white">
      <div className="mx-auto max-w-5xl px-4 py-6 text-center text-sm text-brand-500">
        © {new Date().getFullYear()} AI-Powered E-Commerce Platform
      </div>
    </footer>
  );
}
