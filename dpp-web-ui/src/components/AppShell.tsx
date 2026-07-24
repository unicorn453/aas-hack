import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import EngineeringOutlinedIcon from "@mui/icons-material/EngineeringOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
import LoginIcon from "@mui/icons-material/Login";
import SettingsSuggestOutlinedIcon from "@mui/icons-material/SettingsSuggestOutlined";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import {
  AppBar,
  Box,
  Button,
  CircularProgress,
  Container,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import type { PropsWithChildren } from "react";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "./StatusBadge";

interface AppShellProps extends PropsWithChildren {
  mode: "light" | "dark";
  toggleMode: () => void;
  publicConnected: boolean;
  lastRefresh?: Date;
  onOpenUpload: () => void;
}

function timeLabel(date?: Date): string {
  return date
    ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "Awaiting API";
}

export function AppShell({
  mode,
  toggleMode,
  publicConnected,
  lastRefresh,
  onOpenUpload,
  children,
}: AppShellProps) {
  const auth = useAuth();

  const navigation = [
    { label: "Overview", href: "#overview", icon: <HomeOutlinedIcon /> },
    { label: "DPP record", href: "#dpp", icon: <DescriptionOutlinedIcon /> },
    { label: "Maintenance", href: "#maintenance", icon: <EngineeringOutlinedIcon /> },
    { label: "System", href: "#system", icon: <SettingsSuggestOutlinedIcon /> },
    ...(auth.authenticated
      ? [{ label: "Live telemetry", href: "#telemetry", icon: <AssessmentOutlinedIcon /> }]
      : []),
  ];

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar
        position="sticky"
        color="transparent"
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          backdropFilter: "blur(18px)",
          backgroundColor: (theme) =>
            theme.palette.mode === "dark"
              ? "rgba(7, 17, 30, .88)"
              : "rgba(238, 243, 247, .88)",
        }}
      >
        <Container maxWidth="xl">
          <Toolbar disableGutters sx={{ minHeight: { xs: 72, md: 82 }, gap: 2 }}>
            <Box className="brand-mark" aria-hidden="true">
              <span />
              <span />
            </Box>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="overline" color="primary.main" sx={{ lineHeight: 1 }}>
                Digital Product Passport
              </Typography>
              <Typography
                variant="h6"
                component="div"
                noWrap
                sx={{ fontWeight: 760, lineHeight: 1.25 }}
              >
                Schunk PGN+ P 64-1
              </Typography>
            </Box>

            <Stack
              direction="row"
              spacing={1.25}
              alignItems="center"
              sx={{ display: { xs: "none", md: "flex" } }}
            >
              <StatusBadge
                label={publicConnected ? "Public API online" : "Public API unavailable"}
                tone={publicConnected ? "success" : "error"}
              />
              <Typography variant="caption" color="text.secondary">
                Refreshed {timeLabel(lastRefresh)}
              </Typography>
            </Stack>

            <Tooltip title={`Use ${mode === "dark" ? "light" : "dark"} theme`}>
              <IconButton
                onClick={toggleMode}
                aria-label={`Switch to ${mode === "dark" ? "light" : "dark"} theme`}
              >
                {mode === "dark" ? <LightModeOutlinedIcon /> : <DarkModeOutlinedIcon />}
              </IconButton>
            </Tooltip>

            {auth.status === "initializing" ? (
              <CircularProgress size={24} aria-label="Checking login session" />
            ) : auth.authenticated ? (
              <>
                <Button
                  variant="outlined"
                  color="inherit"
                  startIcon={<CloudUploadOutlinedIcon />}
                  onClick={onOpenUpload}
                  aria-label="Upload AASX asset"
                >
                  <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>
                    Upload AASX
                  </Box>
                </Button>
                <Button
                  variant="outlined"
                  color="inherit"
                  startIcon={<LogoutIcon />}
                  onClick={() => void auth.logout()}
                  disabled={auth.status === "logging-out"}
                  aria-label={`Log out ${auth.user?.username ?? "current user"}`}
                >
                  <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>
                    {auth.status === "logging-out" ? "Logging out…" : "Log out"}
                  </Box>
                </Button>
              </>
            ) : (
              <Button
                variant="contained"
                startIcon={<LoginIcon />}
                onClick={() => void auth.login()}
              >
                Admin login
              </Button>
            )}
          </Toolbar>
        </Container>
      </AppBar>
      <Box className="workspace-layout">
        <Box component="nav" className="workspace-rail" aria-label="Asset workspace navigation">
          <Typography variant="overline" color="text.secondary" sx={{ px: 1.5, mb: 1 }}>
            Asset workspace
          </Typography>
          <Stack spacing={0.5}>
            {navigation.map((item) => (
              <Button
                key={item.href}
                component="a"
                href={item.href}
                variant="text"
                color="inherit"
                startIcon={item.icon}
                sx={{ justifyContent: "flex-start", px: 1.5, py: 1.15, borderRadius: 2 }}
              >
                {item.label}
              </Button>
            ))}
          </Stack>
          {auth.authenticated && <Box className="rail-note">
            <Typography variant="caption" color="text.secondary">
              Read-only DPP workspace
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}>
              Live measurements require administrator access.
            </Typography>
          </Box>}
        </Box>
        <Box component="main" className="workspace-content">{children}</Box>
      </Box>
    </Box>
  );
}
