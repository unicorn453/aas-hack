import { CssBaseline, ThemeProvider } from "@mui/material";
import { useMemo, useState } from "react";
import { AuthProvider } from "./auth/AuthContext";
import { AasxUploadDialog } from "./components/AasxUploadDialog";
import { AppShell } from "./components/AppShell";
import { usePublicDpp } from "./hooks/usePublicDpp";
import { DashboardPage } from "./pages/DashboardPage";
import { createIndustrialTheme } from "./theme";

function DashboardApplication({
  mode,
  toggleMode,
}: {
  mode: "light" | "dark";
  toggleMode: () => void;
}) {
  const [uploadOpen, setUploadOpen] = useState(false);
  const status = usePublicDpp();
  return (
    <AppShell
      mode={mode}
      toggleMode={toggleMode}
      publicConnected={Boolean(status.asset) || status.submodels.some((item) => item.data)}
      lastRefresh={status.lastRefresh}
      onOpenUpload={() => setUploadOpen(true)}
      projects={status.projects.map((project) => ({ id: project.id, name: project.asset.name }))}
      selectedProjectId={status.selectedProjectId}
      onSelectProject={status.selectProject}
    >
      <DashboardPage publicDpp={status} />
      <AasxUploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={status.retry}
      />
    </AppShell>
  );
}

export default function App() {
  const [mode, setMode] = useState<"light" | "dark">(() => {
    const stored = localStorage.getItem("dpp-theme");
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia?.("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  });
  const theme = useMemo(() => createIndustrialTheme(mode), [mode]);
  const toggleMode = () => {
    setMode((current) => {
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem("dpp-theme", next);
      return next;
    });
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <DashboardApplication mode={mode} toggleMode={toggleMode} />
      </AuthProvider>
    </ThemeProvider>
  );
}
