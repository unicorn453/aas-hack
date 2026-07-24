export type ImportResult = {
  fileName: string;
  message: string;
  importId: string;
};

export class ImportApiError extends Error {
  constructor(
    message: string,
    readonly details: string[],
  ) {
    super(message);
    this.name = "ImportApiError";
  }
}

const supportedExtensions = [".aasx"];

/**
 * Mock import boundary. The live implementation should POST FormData to
 * /api/admin/import with the selected file under the field name `file`.
 */
export async function importProductFile(file: File, accessToken?: string): Promise<ImportResult> {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!supportedExtensions.includes(extension)) {
    throw new ImportApiError("Unsupported file type", [
      "Choose an .aasx file.",
    ]);
  }
  if (file.size === 0) {
    throw new ImportApiError("The selected file is empty", [
      "Export the source file again and retry the import.",
    ]);
  }

  return importProductFileLive(file, accessToken);
}

export async function importProductFileLive(file: File, accessToken?: string): Promise<ImportResult> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/upload", {
    method: "POST",
    body,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  const payload = (await response.json()) as ImportResult & {
    message?: string;
    details?: string[];
    error?: string;
  };
  if (!response.ok) {
    throw new ImportApiError(
      payload.message ?? payload.error ?? "The import service rejected the file.",
      payload.details ?? [payload.error ?? "Authentication or import failed."],
    );
  }
  return payload;
}
