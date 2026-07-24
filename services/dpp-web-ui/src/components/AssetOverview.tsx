import PrecisionManufacturingIcon from "@mui/icons-material/PrecisionManufacturing";
import RefreshIcon from "@mui/icons-material/Refresh";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
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
import { useEffect, useState } from "react";
import type { AssetOverview as AssetOverviewModel } from "../types/aas";
import type { AssetMedia } from "../types/aas";

interface AssetOverviewProps {
  loading: boolean;
  asset?: AssetOverviewModel;
  error?: Error;
  onRetry: () => void;
  media: AssetMedia[];
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
  media,
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
            <CompanyLogo media={media} />
            <Stack direction="row" spacing={1} alignItems="center" mb={2}>
              <Chip size="small" color="primary" label="PUBLIC DPP" />
              <Typography variant="overline" color="text.secondary">
                AAS record · public read access
              </Typography>
            </Stack>
            <Typography component="h1" variant="h1" sx={{ maxWidth: 760 }}>
              {asset.name}
            </Typography>
            <Typography variant="h5" color="text.secondary" sx={{ mt: 2, maxWidth: 720, lineHeight: 1.45 }}>
              Structured identity, technical data, documentation and lifecycle information supplied by this AAS.
            </Typography>

            <Grid container spacing={2} sx={{ mt: 3 }}>
              <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                <Detail label="Manufacturer" value={asset.manufacturer} />
              </Grid>
              <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                <Detail label="Product family" value={asset.productFamily} />
              </Grid>
              <Grid size={{ xs: 6, sm: 3, md: 2 }}>
                <Detail label="Asset kind" value={asset.assetKind} />
              </Grid>
              <Grid size={{ xs: 6, sm: 3, md: 4 }}>
                <Detail label="Asset type" value={asset.assetType} />
              </Grid>
            </Grid>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <MediaPanel media={media} assetName={asset.name} />
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

function CompanyLogo({ media }: { media: AssetMedia[] }) {
  const logo = media.find((item) => item.kind === "image" && item.role === "logo");
  return (
    <Box className="company-logo-wrap">
      {logo ? (
        <Box component="img" src={logo.url} alt={logo.label} className="company-logo-image" />
      ) : (
        <Typography variant="caption" color="text.secondary">Company logo not supplied by the AAS</Typography>
      )}
    </Box>
  );
}

function MediaPanel({ media, assetName }: { media: AssetMedia[]; assetName: string }) {
  const images = media.filter((item) => item.kind === "image" && item.role !== "logo");
  const documents = media.filter((item) => item.kind === "document");
  const [selected, setSelected] = useState(images[0]);
  useEffect(() => setSelected(images[0]), [media]);
  return (
    <Box className="asset-media-panel">
      <Box className="asset-media-stage">
        {selected ? (
          <Box component="img" src={selected.url} alt={selected.label || assetName} className="asset-media-image" />
        ) : (
          <Box className="asset-media-empty">
            <PrecisionManufacturingIcon sx={{ fontSize: 54 }} />
            <Typography variant="caption">No product image supplied by the AAS</Typography>
          </Box>
        )}
      </Box>
      {images.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ mt: 1, overflowX: "auto" }}>
          {images.map((item) => (
            <Button key={item.url} onClick={() => setSelected(item)} className="media-thumb" aria-label={`Show ${item.label}`}>
              <Box component="img" src={item.url} alt={item.label} />
            </Button>
          ))}
        </Stack>
      )}
      {documents.length > 0 && (
        <Stack spacing={0.5} sx={{ mt: 1.5 }}>
          <Typography variant="caption" color="text.secondary">Documents from the AAS</Typography>
          {documents.slice(0, 3).map((item) => (
            <Button
              key={item.url}
              component="a"
              href={item.url}
              target="_blank"
              rel="noreferrer"
              startIcon={<PictureAsPdfOutlinedIcon />}
              className="asset-document-link"
            >
              {item.label}
            </Button>
          ))}
        </Stack>
      )}
    </Box>
  );
}
