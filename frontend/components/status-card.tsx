import type { LucideIcon } from "lucide-react";

interface StatusCardProps {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: "healthy" | "neutral" | "warning";
}

export function StatusCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "neutral",
}: StatusCardProps) {
  return (
    <article className={`status-card status-${tone}`}>
      <div className="status-card-head">
        <span>{label}</span>
        <Icon size={17} />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

