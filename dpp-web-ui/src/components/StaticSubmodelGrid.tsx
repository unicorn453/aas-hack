import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import BuildOutlinedIcon from "@mui/icons-material/BuildOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import EnergySavingsLeafOutlinedIcon from "@mui/icons-material/EnergySavingsLeafOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Grid,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import type { SvgIconComponent } from "@mui/icons-material";
import type { PublicSubmodelResult } from "../data/submodelRepository";
import { StatusBadge } from "./StatusBadge";

const icons: Record<string, SvgIconComponent> = {
  badge: BadgeOutlinedIcon,
  settings: SettingsOutlinedIcon,
  eco: EnergySavingsLeafOutlinedIcon,
  build: BuildOutlinedIcon,
  description: DescriptionOutlinedIcon,
};

interface StaticSubmodelGridProps {
  loading: boolean;
  submodels: PublicSubmodelResult[];
  onOpen: (submodel: PublicSubmodelResult) => void;
}

export function StaticSubmodelGrid({
  loading,
  submodels,
  onOpen,
}: StaticSubmodelGridProps) {
  if (loading) {
    return (
      <Grid container spacing={2}>
        {Array.from({ length: 5 }).map((_, index) => (
          <Grid key={index} size={{ xs: 12, sm: 6, lg: index < 3 ? 4 : 6 }}>
            <Skeleton variant="rounded" height={260} />
          </Grid>
        ))}
      </Grid>
    );
  }

  return (
    <Grid container spacing={2}>
      {submodels.map((item, index) => {
        const Icon = icons[item.definition.icon] ?? DescriptionOutlinedIcon;
        const available = Boolean(item.data);
        return (
          <Grid
            key={item.definition.id}
            size={{ xs: 12, sm: 6, lg: index < 3 ? 4 : 6 }}
          >
            <Card className="submodel-card">
              <CardContent sx={{ p: 3, pb: 1.5, flex: 1 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box className="submodel-icon">
                    <Icon />
                  </Box>
                  <StatusBadge
                    label={available ? "Available" : "Unavailable"}
                    tone={available ? "success" : "error"}
                  />
                </Stack>
                <Typography component="h3" variant="h3" mt={3}>
                  {item.definition.title}
                </Typography>
                <Typography color="text.secondary" mt={1} sx={{ minHeight: 66 }}>
                  {item.definition.description}
                </Typography>
                <Tooltip title={item.definition.id}>
                  <Typography
                    variant="caption"
                    color="primary.main"
                    sx={{ display: "block", mt: 2, fontWeight: 750 }}
                  >
                    {item.definition.template}
                  </Typography>
                </Tooltip>
                {item.error && (
                  <Typography variant="caption" color="error.main" sx={{ display: "block", mt: 1 }}>
                    {item.error.message}
                  </Typography>
                )}
              </CardContent>
              <CardActions sx={{ px: 3, pb: 3 }}>
                <Button
                  fullWidth
                  variant={available ? "outlined" : "text"}
                  endIcon={<OpenInNewIcon />}
                  onClick={() => onOpen(item)}
                  aria-label={`Open ${item.definition.title} contents`}
                >
                  {available ? "Explore submodel" : "View error details"}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
}
