export function Footer() {
  return (
    <footer className="border-t border-border/50 py-8">
      <div className="mx-auto flex max-w-6xl items-center justify-center px-4 text-xs text-fg-subtle sm:px-6 lg:px-8">
        <span>© {new Date().getFullYear()} FactGuard</span>
      </div>
    </footer>
  );
}
