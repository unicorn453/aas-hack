import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import LoginIcon from "@mui/icons-material/Login";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { useLiveTelemetry } from "../hooks/useLiveTelemetry";
import { LiveTelemetryDashboard } from "./LiveTelemetryDashboard";

function GateCard({
  icon,
  eyebrow,
  title,
  message,
  action,
  tone = "neutral",
}: {
  icon: ReactNode;
  eyebrow: string;
  title: string;
  message: string;
  action?: ReactNode;
  tone?: "neutral" | "error";
}) {
  return (
    <Card className={tone === "error" ? "gate-card gate-denied" : "gate-card"}>
      <CardContent sx={{ p: { xs: 3, md: 5 } }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={3}
          alignItems={{ md: "center" }}
        >
          <Box className="gate-icon">{icon}</Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="overline" color={tone === "error" ? "error.main" : "primary.main"}>
              {eyebrow}
            </Typography>
            <Typography component="h3" variant="h3">
              {title}
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 720 }}>
              {message}
            </Typography>
          </Box>
          {action}
        </Stack>
      </CardContent>
    </Card>
  );
}

export function TelemetryGate() {
  const auth = useAuth();
  const telemetry = useLiveTelemetry({
    enabled: auth.authenticated && auth.isAdmin,
    getAccessToken: auth.getAccessToken,
  });

  if (auth.status === "initializing" || auth.status === "logging-out") {
    return (
      <GateCard
        icon={<CircularProgress size={32} />}
        eyebrow="Session check"
        title={auth.status === "logging-out" ? "Closing protected session" : "Checking access"}
        message="Static DPP information remains public while the authentication state is verified."
      />
    );
  }

  if (auth.status === "error") {
    return (
      <Alert severity="error" variant="outlined">
        <Typography fontWeight={750}>Authentication service unavailable</Typography>
        {auth.error ?? "Keycloak could not be initialized. Public DPP data remains available."}
      </Alert>
    );
  }

  if (!auth.authenticated) {
    return (
      <GateCard
        icon={<LockOutlinedIcon fontSize="large" />}
        eyebrow="Protected operational data"
        title="Administrator login required"
        message="Asset identity and all five DPP submodels are public. Live measurements are intentionally isolated behind Keycloak and the backend admin role."
        action={
          <Button
            variant="contained"
            size="large"
            startIcon={<LoginIcon />}
            onClick={() => void auth.login()}
          >
            Sign in for telemetry
          </Button>
        }
      />
    );
  }

  if (!auth.isAdmin) {
    return (
      <GateCard
        icon={<ShieldOutlinedIcon fontSize="large" />}
        eyebrow="Access denied"
        title="Administrator permission required"
        message={`You are signed in as ${auth.user?.username ?? "a standard user"}, but your token does not contain the admin realm role. The protected TimeSeries has not been requested.`}
        tone="error"
      />
    );
  }

  if (
    telemetry.connection === "permission-denied" ||
    telemetry.connection === "authentication-failed"
  ) {
    return (
      <GateCard
        icon={<AdminPanelSettingsOutlinedIcon fontSize="large" />}
        eyebrow="Backend authorization"
        title={
          telemetry.connection === "permission-denied"
            ? "Administrator permission denied by backend"
            : "Authentication is no longer valid"
        }
        message={
          telemetry.error ??
          "The protected API rejected this session and live polling has stopped."
        }
        tone="error"
      />
    );
  }

  return <LiveTelemetryDashboard telemetry={telemetry} />;
}
