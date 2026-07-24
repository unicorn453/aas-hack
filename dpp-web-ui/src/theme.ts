import { createTheme, type PaletteMode } from "@mui/material/styles";

export function createIndustrialTheme(mode: PaletteMode) {
  const dark = mode === "dark";
  return createTheme({
    palette: {
      mode,
      primary: { main: dark ? "#f08a6f" : "#c24d3d" },
      secondary: { main: dark ? "#72c9c2" : "#287c78" },
      success: { main: dark ? "#5bd19b" : "#237a52" },
      warning: { main: dark ? "#f3b45d" : "#aa6a18" },
      error: { main: dark ? "#f27d82" : "#b33e3e" },
      background: {
        default: dark ? "#111a1b" : "#f5f7f6",
        paper: dark ? "#182324" : "#ffffff",
      },
      text: {
        primary: dark ? "#eff6f3" : "#1b292b",
        secondary: dark ? "#a8b8b6" : "#657376",
      },
      divider: dark ? "rgba(185, 211, 205, .16)" : "rgba(34, 58, 59, .13)",
    },
    shape: { borderRadius: 11 },
    typography: {
      fontFamily: '"Inter", system-ui, sans-serif',
      h1: { fontSize: "clamp(2.4rem, 5vw, 5.4rem)", fontWeight: 780, lineHeight: .94, letterSpacing: "-.055em" },
      h2: { fontSize: "clamp(1.65rem, 3vw, 2.45rem)", fontWeight: 760, letterSpacing: "-.035em" },
      h3: { fontSize: "1.18rem", fontWeight: 760, letterSpacing: "-.015em" },
      button: { textTransform: "none", fontWeight: 720 },
      overline: { fontWeight: 800, letterSpacing: ".16em", fontSize: ".67rem" },
    },
    components: {
      MuiCard: {
        styleOverrides: {
          root: {
            border: `1px solid ${
              dark ? "rgba(145, 186, 215, .15)" : "rgba(27, 68, 96, .13)"
            }`,
            boxShadow: dark
              ? "0 18px 42px rgba(0, 0, 0, .22)"
              : "0 14px 34px rgba(34, 58, 59, .07)",
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
