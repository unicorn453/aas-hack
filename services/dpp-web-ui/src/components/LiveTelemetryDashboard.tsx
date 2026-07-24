import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import DeviceThermostatOutlinedIcon from "@mui/icons-material/DeviceThermostatOutlined";
import ElectricMeterOutlinedIcon from "@mui/icons-material/ElectricMeterOutlined";
import PanToolAltOutlinedIcon from "@mui/icons-material/PanToolAltOutlined";
import NumbersOutlinedIcon from "@mui/icons-material/NumbersOutlined";
import SensorsOutlinedIcon from "@mui/icons-material/SensorsOutlined";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";
import type { ReactNode } from "react";
import type { LiveTelemetryState } from "../hooks/useLiveTelemetry";
import type { TimeSeriesRecord } from "../types/aas";
import { StatusBadge } from "./StatusBadge";
import { TelemetryChart } from "./TelemetryChart";

interface Metric {
  key: keyof TimeSeriesRecord;
  label: string;
  unit: string;
  decimals: number;
  icon: ReactNode;
  warn?: (value: number) => boolean;
}

const metrics: Metric[] = [
  {
    key: "jawPosition",
    label: "Jaw position",
    unit: "mm",
    decimals: 2,
    icon: <PanToolAltOutlinedIcon />,
    warn: (value) => value < 0 || value > 70,
  },
  {
    key: "gripForce",
    label: "Grip force",
    unit: "N",
    decimals: 2,
    icon: <BoltOutlinedIcon />,
    warn: (value) => value > 100,
  },
  {
    key: "temperature",
    label: "Temperature",
    unit: "°C",
    decimals: 1,
    icon: <DeviceThermostatOutlinedIcon />,
    warn: (value) => value > 50,
  },
  {
    key: "motorCurrent",
    label: "Motor current",
    unit: "A",
    decimals: 2,
    icon: <ElectricMeterOutlinedIcon />,
    warn: (value) => value > 3,
  },
  {
    key: "cycleCount",
    label: "Cycle count",
    unit: "",
    decimals: 0,
    icon: <NumbersOutlinedIcon />,
  },
  {
    key: "currentState",
    label: "Current state",
    unit: "",
    decimals: 0,
    icon: <SensorsOutlinedIcon />,
  },
];

function trendFor(
  metric: Metric,
  latest: TimeSeriesRecord,
  previous?: TimeSeriesRecord,
): string {
  if (!previous || metric.key === "currentState") return "No prior sample";
  const current = Number(latest[metric.key]);
  const prior = Number(previous[metric.key]);
  if (!Number.isFinite(current) || !Number.isFinite(prior)) return "State signal";
  const difference = current - prior;
  if (Math.abs(difference) < 0.001) return "→ Stable";
  return `${difference > 0 ? "↑" : "↓"} ${Math.abs(difference).toFixed(metric.decimals)}`;
}

function connectionTone(
  connection: LiveTelemetryState["connection"],
): "success" | "warning" | "error" | "info" {
  if (connection === "connected") return "success";
  if (connection === "connecting") return "info";
  if (connection === "stale" || connection === "unavailable") return "warning";
  return "error";
}

interface LiveTelemetryDashboardProps {
  telemetry: LiveTelemetryState;
}

function downloadRecords(records: TimeSeriesRecord[], format: "csv" | "json") {
  const payload = format === "json"
    ? JSON.stringify(records, null, 2)
    : [
        "observedAt,jawPosition,gripForce,temperature,motorCurrent,cycleCount,currentState",
        ...records.map((record) => [
          record.observedAt,
          record.jawPosition,
          record.gripForce,
          record.temperature,
          record.motorCurrent,
          record.cycleCount,
          record.currentState,
        ].map((value) => JSON.stringify(value)).join(",")),
      ].join("\\n");
  const blob = new Blob([payload], { type: format === "json" ? "application/json" : "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `pgn-plus-telemetry.${format}`;
  link.click();
  URL.revokeObjectURL(url);
}

export function LiveTelemetryDashboard({
  telemetry,
}: LiveTelemetryDashboardProps) {
  const latest = telemetry.records.at(-1);
  const previous = telemetry.records.at(-2);
  const loading = telemetry.connection === "connecting" && !latest;

  return (
    <Stack spacing={2.5}>
      <Card className="live-status-card">
        <CardContent>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            spacing={2}
            alignItems={{ sm: "center" }}
          >
            <Box>
              <Typography variant="overline" color="primary.main">
                Protected TimeSeries · admin
              </Typography>
              <Typography component="h3" variant="h3">
                Live machine signal
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <StatusBadge
                label={telemetry.connection.replace(/-/g, " ")}
                tone={connectionTone(telemetry.connection)}
              />
              <Typography variant="caption" color="text.secondary">
                Last API update:{" "}
                {telemetry.lastSuccessAt
                  ? telemetry.lastSuccessAt.toLocaleTimeString()
                  : "waiting"}
              </Typography>
            </Stack>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mt: 2 }} flexWrap="wrap">
            <Button
              size="small"
              variant="outlined"
              startIcon={<DownloadOutlinedIcon />}
              onClick={() => downloadRecords(telemetry.records, "csv")}
              disabled={!telemetry.records.length}
            >
              Export CSV
            </Button>
            <Button
              size="small"
              variant="text"
              onClick={() => downloadRecords(telemetry.records, "json")}
              disabled={!telemetry.records.length}
            >
              Export JSON
            </Button>
          </Stack>
          {loading && <LinearProgress sx={{ mt: 2 }} aria-label="Loading live telemetry" />}
        </CardContent>
      </Card>

      {telemetry.error && (
        <Alert
          severity={
            telemetry.connection === "permission-denied" ||
            telemetry.connection === "authentication-failed" ||
            telemetry.connection === "not-found"
              ? "error"
              : "warning"
          }
        >
          <Typography fontWeight={750}>
            {telemetry.connection === "stale"
              ? "Telemetry data is stale"
              : "Live connection issue"}
          </Typography>
          {telemetry.error}
        </Alert>
      )}

      <Grid container spacing={2}>
        {metrics.map((metric) => {
          const raw = latest?.[metric.key];
          const numeric = Number(raw);
          const warning =
            latest && Number.isFinite(numeric) && metric.warn?.(numeric);
          const value =
            raw === undefined
              ? "—"
              : metric.key === "currentState"
                ? String(raw)
                : Number(raw).toFixed(metric.decimals);
          return (
            <Grid key={metric.key} size={{ xs: 6, md: 4, lg: 2 }}>
              <Card className={warning ? "kpi-card kpi-warning" : "kpi-card"}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" color="primary.main">
                    <Box className="kpi-icon">{metric.icon}</Box>
                    {warning && <StatusBadge label="Check" tone="warning" />}
                  </Stack>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
                    {metric.label}
                  </Typography>
                  <Typography className="kpi-value" title={`${value} ${metric.unit}`}>
                    {value}
                    {metric.unit && <small>{metric.unit}</small>}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {latest ? trendFor(metric, latest, previous) : "Awaiting first sample"}
                  </Typography>
                  {latest && (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block" }}
                    >
                      Sample{" "}
                      {new Date(latest.observedAt).toLocaleTimeString([], {
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {latest ? (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 6 }}>
            <TelemetryChart
              title="Jaw position"
              dataKey="jawPosition"
              unit="mm"
              records={telemetry.records}
              color="#42c8f5"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <TelemetryChart
              title="Grip force"
              dataKey="gripForce"
              unit="N"
              records={telemetry.records}
              color="#8b9cff"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <TelemetryChart
              title="Temperature"
              dataKey="temperature"
              unit="°C"
              records={telemetry.records}
              color="#f4a340"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <TelemetryChart
              title="Motor current"
              dataKey="motorCurrent"
              unit="A"
              records={telemetry.records}
              color="#35c98d"
            />
          </Grid>
        </Grid>
      ) : (
        <Card>
          <CardContent sx={{ py: 6, textAlign: "center" }}>
            <SensorsOutlinedIcon color="disabled" sx={{ fontSize: 44 }} />
            <Typography mt={1.5} fontWeight={750}>
              Waiting for the protected TimeSeries
            </Typography>
            <Typography color="text.secondary">
              The first sample will appear after authentication and a successful API read.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
