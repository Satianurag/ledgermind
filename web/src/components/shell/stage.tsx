import { cn } from "@/lib/utils";

/** One beat on stage: a heading that states the claim, then the evidence for it. */
export function Stage({
  eyebrow,
  title,
  claim,
  action,
  children,
  className,
}: {
  eyebrow: string;
  title: string;
  claim: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("space-y-6", className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl space-y-1.5">
          <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {eyebrow}
          </span>
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="text-sm leading-relaxed text-muted-foreground">{claim}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
