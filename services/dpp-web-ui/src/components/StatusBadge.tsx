import CircleIcon from "@mui/icons-material/Circle";
import { Chip, type ChipProps } from "@mui/material";

type StatusTone = "success" | "info" | "warning" | "error" | "neutral";

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
  size?: ChipProps["size"];
}

const colors: Record<StatusTone, ChipProps["color"]> = {
  success: "success",
  info: "info",
  warning: "warning",
  error: "error",
  neutral: "default",
};

export function StatusBadge({
  label,
  tone = "neutral",
  size = "small",
}: StatusBadgeProps) {
  return (
    <Chip
      size={size}
      color={colors[tone]}
      variant={tone === "neutral" ? "outlined" : "filled"}
      icon={<CircleIcon sx={{ fontSize: "9px !important" }} />}
      label={label}
      sx={{ fontWeight: 750 }}
    />
  );
}
