export function LoadingDots({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-ink-500 dark:text-ink-400 text-sm">
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-brand-500 animate-bounce [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 rounded-full bg-brand-500 animate-bounce [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 rounded-full bg-brand-500 animate-bounce" />
      </span>
      {label && <span>{label}</span>}
    </div>
  );
}
