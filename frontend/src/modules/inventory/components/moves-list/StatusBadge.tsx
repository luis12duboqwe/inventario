import React from "react";

type Props = {
  value: string;
};

export default function StatusBadge({ value }: Props) {
  const map: Record<string, string> = {
    DRAFT: "bg-gray-500/20 text-gray-400",
    PENDING: "bg-sky-500/20 text-sky-400",
    APPROVED: "bg-blue-500/20 text-blue-400",
    PARTIAL: "bg-amber-500/20 text-amber-400",
    DONE: "bg-green-500/20 text-green-400",
    CANCELLED: "bg-red-500/20 text-red-400",
  };
  const className = map[value] || "bg-gray-500/20 text-gray-400";

  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${className}`}>{value}</span>;
}
