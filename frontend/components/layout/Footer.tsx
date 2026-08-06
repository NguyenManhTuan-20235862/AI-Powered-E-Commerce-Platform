export function Footer() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto max-w-5xl px-4 py-6 text-center text-sm text-foreground-muted">
        © {new Date().getFullYear()} Vun - Nền tảng thương mại điện tử
      </div>
    </footer>
  );
}
