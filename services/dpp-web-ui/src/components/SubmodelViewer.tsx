import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import CodeIcon from "@mui/icons-material/Code";
import CloseIcon from "@mui/icons-material/Close";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useMemo, useState } from "react";
import type { PublicSubmodelResult } from "../data/submodelRepository";
import { parseSubmodel } from "../data/submodelParser";
import type { StructuredElement } from "../types/aas";

function ElementTree({
  elements,
  level = 0,
}: {
  elements: StructuredElement[];
  level?: number;
}) {
  return (
    <Stack spacing={1.25}>
      {elements.map((element) =>
        element.children?.length ? (
          <Accordion
            key={element.key}
            defaultExpanded={level === 0}
            disableGutters
            elevation={0}
            sx={{ border: 1, borderColor: "divider", "&:before": { display: "none" } }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls={`${element.key}-content`}
              id={`${element.key}-header`}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography fontWeight={750}>{element.label}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {element.modelType} · {element.children.length} elements
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              {element.description && (
                <Typography variant="body2" color="text.secondary" mb={2}>
                  {element.description}
                </Typography>
              )}
              <ElementTree elements={element.children} level={level + 1} />
            </AccordionDetails>
          </Accordion>
        ) : (
          <Box className="structured-row" key={element.key}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" fontWeight={700}>
                {element.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {element.modelType}
                {element.semanticId ? ` · ${element.semanticId}` : ""}
              </Typography>
            </Box>
            <Typography
              variant="body2"
              className="structured-value"
              title={element.value}
            >
              {element.value ?? "Not provided"}
              {element.unit ? ` ${element.unit}` : ""}
            </Typography>
          </Box>
        ),
      )}
    </Stack>
  );
}

interface SubmodelViewerProps {
  selected?: PublicSubmodelResult;
  onClose: () => void;
}

export function SubmodelViewer({ selected, onClose }: SubmodelViewerProps) {
  const [raw, setRaw] = useState(false);
  const elements = useMemo(
    () => (selected?.data ? parseSubmodel(selected.data) : []),
    [selected],
  );

  const close = () => {
    setRaw(false);
    onClose();
  };

  return (
    <Dialog
      open={Boolean(selected)}
      onClose={close}
      fullWidth
      maxWidth="md"
      scroll="paper"
      aria-labelledby="submodel-dialog-title"
    >
      <DialogTitle component="div" id="submodel-dialog-title" sx={{ pr: 7 }}>
        <Typography variant="overline" color="primary.main">
          Public DPP submodel
        </Typography>
        <Typography variant="h4" fontWeight={760}>
          {selected?.definition.title}
        </Typography>
        <Tooltip title={selected?.definition.id ?? ""}>
          <Typography className="identifier" variant="caption" color="text.secondary">
            {selected?.definition.id}
          </Typography>
        </Tooltip>
        <IconButton
          onClick={close}
          aria-label="Close submodel details"
          sx={{ position: "absolute", right: 16, top: 16 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <Divider />
      <DialogContent sx={{ p: { xs: 2, sm: 3 } }}>
        {selected?.error ? (
          <Alert severity="error">
            <Typography fontWeight={750}>Submodel unavailable</Typography>
            {selected.error.message}
          </Alert>
        ) : raw ? (
          <Box component="pre" className="raw-json" aria-label="Raw submodel JSON">
            {JSON.stringify(selected?.data, null, 2)}
          </Box>
        ) : elements.length ? (
          <ElementTree elements={elements} />
        ) : (
          <Alert severity="info">This submodel contains no readable elements.</Alert>
        )}
      </DialogContent>
      <Divider />
      <DialogActions sx={{ p: 2 }}>
        {selected?.data && (
          <Button
            onClick={() => setRaw((current) => !current)}
            startIcon={raw ? <AccountTreeOutlinedIcon /> : <CodeIcon />}
          >
            {raw ? "Structured view" : "View raw JSON"}
          </Button>
        )}
        <Button variant="contained" onClick={close}>
          Done
        </Button>
      </DialogActions>
    </Dialog>
  );
}
