import { memo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { colorVar, colors, radiusVar, shadowVar } from "../../../theme/designTokens";

export type InventoryCategoryDatum = {
  label: string;
  value: number;
};

type InventoryCategoryChartProps = {
  data: InventoryCategoryDatum[];
  totalUnits: number;
};

const CATEGORY_PALETTE = [
  colors.accentBright,
  colors.accent,
  colors.chartSky,
  colors.chartPurple,
  colors.chartAmber,
  colors.chartOrange,
] as const;

const InventoryCategoryChart = memo(function InventoryCategoryChart({
  data,
  totalUnits,
}: InventoryCategoryChartProps) {
  if (data.length === 0) {
    return <p className="muted-text">Aún no se registra inventario por categoría.</p>;
  }

  return (
    <>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colorVar("accentSoft")} vertical={false} />
          <XAxis
            dataKey="label"
            stroke="var(--text-secondary)"
            tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            stroke="var(--text-secondary)"
            tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ fill: colorVar("accentSoft") }}
            contentStyle={{
              backgroundColor: colorVar("surfaceTooltip"),
              border: `1px solid ${colorVar("accentBorder")}`,
              borderRadius: radiusVar("md"),
              color: colorVar("textPrimary"),
              boxShadow: shadowVar("sm"),
            }}
            labelStyle={{ color: colorVar("accent") }}
            formatter={(value: number) => [
              `${Number(value).toLocaleString("es-MX")} unidades`,
              "Existencias",
            ]}
          />
          <Bar dataKey="value" radius={[12, 12, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={`${entry.label}-${index}`}
                fill={CATEGORY_PALETTE[index % CATEGORY_PALETTE.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <ul className="inventory-category-list">
        {data.map((entry) => {
          const share = totalUnits === 0 ? 0 : Math.round((entry.value / totalUnits) * 100);
          return (
            <li key={entry.label}>
              <span>{entry.label}</span>
              <span>
                {entry.value.toLocaleString("es-MX")} uds · {share}%
              </span>
            </li>
          );
        })}
      </ul>
    </>
  );
});

export default InventoryCategoryChart;
