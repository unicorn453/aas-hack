import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import CheckCircleOutlineOutlinedIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import ErrorOutlineOutlinedIcon from "@mui/icons-material/ErrorOutlineOutlined";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
} from "@mui/material";
import { useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { securedApi } from "../api/securedApi";

interface AasxUploadDialogProps {
  open: boolean;
  onClose: () => void;
}

function responseSummary(response: unknown): string {
  if (typeof response === "string" && response.trim()) return response;
  if (response && typeof response === "object") {
    const value = response as Record<string, unknown>;
    const id = value.id ?? value.aasId ?? value.shellId;
    if (typeof id === "string") return `Created asset: ${id}`;
    return "The AASX file was accepted by the AAS environment.";
  }
  return "The AASX file was accepted by the AAS environment.";
}

export function AasxUploadDialog({ open, onClose }: AasxUploadDialogProps) {
  const auth = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>();
  const [error, setError] = useState<string>();

  const reset = () => {
    setFile(undefined);
    setBusy(false);
    setMessage(undefined);
    setError(undefined);
    if (inputRef.current) inputRef.current.value = "";
  };

  const close = () => {
    if (busy) return;
    reset();
    onClose();
  };

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setError(undefined);
    setMessage(undefined);
    try {
      const result = await securedApi.uploadAasx(file, await auth.getAccessToken());
      setMessage(responseSummary(result));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The AASX upload failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="sm" aria-labelledby="aasx-upload-title">
      <DialogTitle id="aasx-upload-title">Upload AASX asset</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5}>
          <Typography color="text.secondary">
            Upload an Asset Administration Shell package to the protected AAS environment. The file is not made public automatically.
          </Typography>
          <Box
            className="upload-dropzone"
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
            }}
          >
            <CloudUploadOutlinedIcon color="primary" sx={{ fontSize: 42 }} />
            <Typography fontWeight={750}>
              {file ? file.name : "Choose an .aasx file"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Maximum size: 100 MB
            </Typography>
            <input
              ref={inputRef}
              hidden
              type="file"
              accept=".aasx,application/asset-administration-shell-package+xml,application/zip"
              onChange={(event) => {
                const selected = event.target.files?.[0];
                setFile(selected);
                setError(undefined);
                setMessage(undefined);
              }}
            />
          </Box>
          {message && <Alert icon={<CheckCircleOutlineOutlinedIcon />} severity="success">{message}</Alert>}
          {error && <Alert icon={<ErrorOutlineOutlinedIcon />} severity="error">{error}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ p: 2.5 }}>
        <Button onClick={close} disabled={busy}>Close</Button>
        <Button
          variant="contained"
          startIcon={busy ? <CircularProgress size={18} color="inherit" /> : <CloudUploadOutlinedIcon />}
          onClick={() => void upload()}
          disabled={!file || busy || Boolean(message)}
        >
          {busy ? "Uploading…" : "Upload AASX"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
