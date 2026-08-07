// Trang demo TẠM THỜI (task 4.1.1) - xem tổng thể design token áp dụng ra
// site trông thế nào trước khi dùng cho các trang thật (catalog, admin...).
// XÓA file này (và thư mục theme-preview/) khi không còn cần nữa.

function Swatch({ name, className, hexNote }: { name: string; className: string; hexNote: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className={`h-16 rounded-2xl border border-border ${className}`} />
      <div>
        <p className="font-heading text-sm text-foreground">{name}</p>
        <p className="text-xs text-foreground-muted">{hexNote}</p>
      </div>
    </div>
  );
}

export default function ThemePreviewPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-12 px-4 py-10">
      <header>
        <h1 className="font-heading text-3xl text-foreground">Design Tokens - Vun</h1>
        <p className="mt-2 text-foreground-muted">
          Trích xuất từ theme trang đăng nhập/đăng ký (task 1.3.4), chuẩn hóa thành token dùng chung
          toàn site (task 4.1.1).
        </p>
      </header>

      <section>
        <h2 className="mb-4 font-heading text-xl text-foreground">Màu sắc</h2>
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <Swatch name="background" className="bg-background" hexNote="#f5ead8" />
          <Swatch name="surface" className="bg-surface" hexNote="#ebddc5" />
          <Swatch name="primary" className="bg-primary" hexNote="#c67139" />
          <Swatch name="primary-hover" className="bg-primary-hover" hexNote="#b2622d" />
          <Swatch name="primary-100" className="bg-primary-100" hexNote="#fff2eb" />
          <Swatch name="primary-300" className="bg-primary-300" hexNote="#ffc6a5" />
          <Swatch name="primary-700" className="bg-primary-700" hexNote="#8c491a" />
          <Swatch name="primary-800" className="bg-primary-800" hexNote="#643312" />
          <Swatch name="secondary" className="bg-secondary" hexNote="#7a8a5e" />
          <Swatch name="secondary-100" className="bg-secondary-100" hexNote="#f0fae1" />
          <Swatch name="secondary-300" className="bg-secondary-300" hexNote="#ccdbb2" />
          <Swatch name="secondary-800" className="bg-secondary-800" hexNote="#3d472b" />
          <Swatch name="foreground" className="bg-foreground" hexNote="#201e1d" />
          <Swatch name="foreground-secondary" className="bg-foreground-secondary" hexNote="#645c50" />
          <Swatch name="foreground-muted" className="bg-foreground-muted" hexNote="#82796a" />
          <Swatch name="border" className="bg-border" hexNote="text 16% opacity" />
        </div>
      </section>

      <section>
        <h2 className="mb-4 font-heading text-xl text-foreground">Font</h2>
        <div className="space-y-3">
          <p className="font-heading text-3xl text-foreground">Font heading - Caprasimo</p>
          <p className="font-body text-base text-foreground">
            Font body - Figtree. Đoạn văn bản thường dùng font này, kể cả input/label/paragraph.
          </p>
        </div>
      </section>

      <section>
        <h2 className="mb-4 font-heading text-xl text-foreground">Component mẫu</h2>
        <div className="flex flex-wrap items-center gap-4">
          <button className="rounded-full bg-primary px-4 py-2 font-heading text-sm text-background hover:bg-primary-hover">
            Button primary
          </button>
          <button className="rounded-full bg-primary-100 px-4 py-2 font-heading text-sm text-primary-800 hover:bg-primary-300">
            Button secondary
          </button>
          <input
            className="min-h-[36px] rounded-full border border-border bg-surface px-4 py-1.5 text-sm text-foreground"
            placeholder="Input mẫu"
          />
        </div>

        <div className="mt-6 max-w-sm rounded-2xl border border-border bg-surface p-6 shadow-warm">
          <p className="font-heading text-lg text-foreground">Card mẫu</p>
          <p className="mt-2 text-sm text-foreground-muted">
            Card dùng nền surface (khác nền trang background), bo góc rounded-2xl (=radius-md 16px),
            đổ bóng shadow-warm.
          </p>
        </div>
      </section>
    </div>
  );
}
