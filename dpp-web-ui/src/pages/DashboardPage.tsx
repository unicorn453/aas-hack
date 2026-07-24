import {
  Box,
  Container,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { config } from "../config";
import type { PublicSubmodelResult } from "../data/submodelRepository";
import { usePublicDpp } from "../hooks/usePublicDpp";
import { AssetOverview } from "../components/AssetOverview";
import { StaticSubmodelGrid } from "../components/StaticSubmodelGrid";
import { SubmodelViewer } from "../components/SubmodelViewer";
import { TelemetryGate } from "../components/TelemetryGate";
import { StatusBadge } from "../components/StatusBadge";

interface DashboardPageProps {
  publicDpp: ReturnType<typeof usePublicDpp>;
}

export function DashboardPage({ publicDpp }: DashboardPageProps) {
  const auth = useAuth();
  const [selected, setSelected] = useState<PublicSubmodelResult>();
  const availableCount = publicDpp.submodels.filter((item) => item.data).length;

  return (
    <>
      <Container maxWidth="xl" sx={{ py: { xs: 3, md: 5 } }}>
        <Box component="section" id="overview" aria-labelledby="overview-heading">
          <Box className="section-kicker" sx={{ mb: 1.5 }}>Asset overview</Box>
          <AssetOverview
            loading={publicDpp.loading}
            asset={publicDpp.asset}
            error={publicDpp.assetError}
            onRetry={publicDpp.retry}
          />
        </Box>

        <Box component="section" id="dpp" aria-labelledby="dpp-heading" sx={{ mt: { xs: 6, md: 9 } }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ sm: "end" }}
            spacing={2}
            mb={3}
          >
            <Box>
              <Box className="section-kicker">Static product record</Box>
              <Typography id="dpp-heading" component="h2" variant="h2">
                Digital Product Passport
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 710 }}>
                Explore the machine-readable identity, specifications and lifecycle
                documents exposed through the anonymous read-only facade.
              </Typography>
            </Box>
            {!publicDpp.loading && (
              <StatusBadge
                label={`${availableCount} of 5 submodels available`}
                tone={availableCount === 5 ? "success" : availableCount ? "warning" : "error"}
                size="medium"
              />
            )}
          </Stack>
          <StaticSubmodelGrid
            loading={publicDpp.loading}
            submodels={publicDpp.submodels}
            onOpen={setSelected}
          />
        </Box>

        {auth.authenticated && <Box
          component="section"
          id="telemetry"
          aria-labelledby="telemetry-heading"
          className="telemetry-section"
          sx={{ mt: { xs: 7, md: 10 } }}
        >
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ sm: "end" }}
            spacing={2}
            mb={3}
          >
            <Box>
              <Box className="section-kicker">
                <span className={auth.isAdmin ? "live-pulse" : undefined} />
                Operational layer
              </Box>
              <Typography id="telemetry-heading" component="h2" variant="h2">
                Live telemetry
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 710 }}>
                A two-second operational view of the machine signals available to your account.
              </Typography>
            </Box>
            <StatusBadge
              label={auth.isAdmin ? "Admin session" : "Protected"}
              tone={auth.isAdmin ? "success" : "neutral"}
              size="medium"
            />
          </Stack>
          <TelemetryGate />
        </Box>}

        <Box component="section" id="maintenance" aria-labelledby="maintenance-heading" sx={{ mt: { xs: 7, md: 10 } }}>
          <Box className="section-kicker">Service workspace</Box>
          <Typography id="maintenance-heading" component="h2" variant="h2">
            Maintenance and handover
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 710, mb: 3 }}>
            Maintenance instructions and handover documentation are available from the public DPP record. Open the corresponding cards above to inspect their structured contents.
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <StatusBadge label="Maintenance instructions public" tone="success" size="medium" />
            <StatusBadge label="Handover documentation public" tone="success" size="medium" />
            <StatusBadge label="Machine control disabled" tone="neutral" size="medium" />
          </Stack>
        </Box>
      </Container>

      <Box component="footer" id="system" sx={{ borderTop: 1, borderColor: "divider", mt: 8 }}>
        <Container maxWidth="xl" sx={{ py: 3 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={{ xs: 1.5, md: 3 }}
            divider={<Divider orientation="vertical" flexItem />}
          >
            <Typography variant="caption" color="text.secondary">
              {auth.authenticated
                ? "Endpoint mode: public DPP + account-protected operational data"
                : "Endpoint mode: public DPP record"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              User: {auth.user?.username ?? "anonymous"}
            </Typography>
            <Typography variant="caption" color="text.secondary" className="identifier">
              AAS: {config.aasId}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ ml: { md: "auto !important" } }}>
              Read-only industrial monitoring interface
            </Typography>
          </Stack>
        </Container>
      </Box>

      <SubmodelViewer selected={selected} onClose={() => setSelected(undefined)} />
    </>
  );
}
