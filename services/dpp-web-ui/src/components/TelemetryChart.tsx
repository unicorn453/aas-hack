import { Box, Card, CardContent, Typography, useTheme } from "@mui/material";
import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimeSeriesRecord } from "../types/aas";

type NumericTelemetryKey =
  | "jawPosition"
  | "gripForce"
  | "temperature"
  | "motorCurrent";

interface TelemetryChartProps {
  title: string;
  dataKey: NumericTelemetryKey;
  unit: string;
  records: TimeSeriesRecord[];
  color: string;
}

function tickTime(value: string): string {
  return new Date(value).toLocaleTimeString([], {
    minute: "2-digit",
    second: "2-digit",
  });
}

export function TelemetryChart({
  title,
  dataKey,
  unit,
  records,
  color,
}: TelemetryChartProps) {
  const theme = useTheme();
  return (
    <Card className="chart-card">
      <CardContent>
        <Box className="chart-heading">
          <Box>
            <Typography component="h4" fontWeight={750}>
              {title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Recent samples · {records.length} points
            </Typography>
          </Box>
          <Typography className="chart-unit" variant="caption">{unit || "signal"}</Typography>
        </Box>
        <Box
          sx={{ width: "100%", height: 240 }}
          role="img"
          aria-label={`${title} time-series chart with ${records.length} recent samples`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={records} margin={{ top: 8, right: 10, bottom: 0, left: -12 }}>
              <defs>
                <linearGradient id={`fill-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.24} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.015} />
                </linearGradient>
              </defs>
              <CartesianGrid
                stroke={theme.palette.divider}
                strokeDasharray="4 4"
                vertical={false}
              />
              <XAxis
                dataKey="observedAt"
                tickFormatter={tickTime}
                tick={{ fill: theme.palette.text.secondary, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                minTickGap={28}
              />
              <YAxis
                tick={{ fill: theme.palette.text.secondary, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={48}
                unit={unit}
                domain={["auto", "auto"]}
              />
              <Tooltip
                labelFormatter={(value) =>
                  new Date(String(value)).toLocaleString()
                }
                formatter={(value) => [`${Number(value).toFixed(2)} ${unit}`, title]}
                contentStyle={{
                  borderRadius: 10,
                  border: `1px solid ${theme.palette.divider}`,
                  background: theme.palette.background.paper,
                  color: theme.palette.text.primary,
                }}
              />
              <Area
                type="monotone"
                dataKey={dataKey}
                stroke="none"
                fill={`url(#fill-${dataKey})`}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey={dataKey}
                name={title}
                stroke={color}
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}
