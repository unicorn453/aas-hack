import PrecisionManufacturingIcon from "@mui/icons-material/PrecisionManufacturing";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import type { AssetOverview as AssetOverviewModel } from "../types/aas";

interface AssetOverviewProps {
  loading: boolean;
  asset?: AssetOverviewModel;
  error?: Error;
  onRetry: () => void;
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography className="identifier" variant="body2" title={value}>
        {value}
      </Typography>
    </Box>
  );
}

export function AssetOverview({
  loading,
  asset,
  error,
  onRetry,
}: AssetOverviewProps) {
  if (loading) {
    return (
      <Card aria-label="Loading asset information">
        <CardContent sx={{ p: { xs: 3, md: 5 } }}>
          <Skeleton width={140} />
          <Skeleton variant="text" width="55%" height={72} />
          <Skeleton variant="rounded" height={116} sx={{ mt: 3 }} />
        </CardContent>
      </Card>
    );
  }

  if (error || !asset) {
    return (
      <Alert
        severity="error"
        variant="outlined"
        action={
          <Button color="inherit" startIcon={<RefreshIcon />} onClick={onRetry}>
            Retry
          </Button>
        }
      >
        <Typography fontWeight={750}>Public asset could not be loaded</Typography>
        <Typography variant="body2">
          {error?.message ??
            "The configured AAS was not returned by the public DPP facade."}
        </Typography>
      </Alert>
    );
  }

  return (
    <Card className="hero-card">
      <CardContent sx={{ p: { xs: 3, md: 5 } }}>
        <Grid container spacing={{ xs: 3, md: 5 }} alignItems="center">
          <Grid size={{ xs: 12, md: 8 }}>
            <Stack direction="row" spacing={1} alignItems="center" mb={2}>
              <Chip size="small" color="primary" label="PUBLIC DPP" />
              <Typography variant="overline" color="text.secondary">
                Industrial component · verified source
              </Typography>
            </Stack>
            <Typography component="h1" variant="h1" sx={{ maxWidth: 760 }}>
              {asset.name}
            </Typography>
            <Typography
              variant="h5"
              color="text.secondary"
              sx={{ mt: 2, maxWidth: 720, lineHeight: 1.45 }}
            >
              Pneumatic universal gripper identity, technical documentation and
              lifecycle information.
            </Typography>

            <Grid container spacing={2} sx={{ mt: 3 }}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Detail label="Manufacturer" value={asset.manufacturer} />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Detail label="Product family" value={asset.productFamily} />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Detail label="Asset kind" value={asset.assetKind} />
              </Grid>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Detail label="Asset type" value={asset.assetType} />
              </Grid>
            </Grid>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Box className="gripper-visual" role="img" aria-label="Abstract parallel gripper">
              <div className="gripper-jaw jaw-left" />
              <div className="gripper-jaw jaw-right" />
              <div className="gripper-body">
                <PrecisionManufacturingIcon />
                <span>PGN+ P 64-1</span>
              </div>
            </Box>
          </Grid>
        </Grid>

        <Box className="asset-id-panel">
          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Detail label="Global asset ID" value={asset.globalAssetId} />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Detail label="Asset Administration Shell ID" value={asset.aasId} />
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );
}
