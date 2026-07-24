import { createTheme, type PaletteMode } from "@mui/material/styles";

export function createIndustrialTheme(mode: PaletteMode) {
  const dark = mode === "dark";
  return createTheme({
    palette: {
      mode,
      primary: { main: dark ? "#42c8f5" : "#0079a8" },
      secondary: { main: "#7c8cff" },
      success: { main: "#35c98d" },
      warning: { main: "#f4a340" },
      error: { main: "#ef6070" },
      background: {
        default: dark ? "#07111e" : "#eef3f7",
        paper: dark ? "#0d1a2a" : "#ffffff",
      },
      text: {
        primary: dark ? "#eef7ff" : "#102335",
        secondary: dark ? "#95a9bd" : "#536779",
      },
      divider: dark ? "rgba(145, 186, 215, .16)" : "rgba(27, 68, 96, .14)",
    },
    shape: { borderRadius: 14 },
    typography: {
      fontFamily: '"Inter", system-ui, sans-serif',
      h1: { fontSize: "clamp(2rem, 5vw, 4.5rem)", fontWeight: 760, lineHeight: 1 },
      h2: { fontSize: "clamp(1.55rem, 3vw, 2.25rem)", fontWeight: 720 },
      h3: { fontSize: "1.25rem", fontWeight: 700 },
      button: { textTransform: "none", fontWeight: 700 },
      overline: { fontWeight: 800, letterSpacing: ".14em" },
    },
    components: {
      MuiCard: {
        styleOverrides: {
          root: {
            border: `1px solid ${
              dark ? "rgba(145, 186, 215, .15)" : "rgba(27, 68, 96, .13)"
            }`,
            boxShadow: dark
              ? "0 18px 42px rgba(0, 0, 0, .20)"
              : "0 16px 36px rgba(26, 62, 88, .08)",
            backgroundImage: "none",
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
      },
      MuiTooltip: {
        defaultProps: { arrow: true },
      },
    },
  });
}
