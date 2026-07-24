"use client";

import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { Icon } from "./icons";
import { ImportApiError, importProductFile, type ImportResult } from "@/lib/import/import-api";

type UploadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: ImportResult }
  | { status: "error"; message: string; details: string[] };

export function AdminUploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [state, setState] = useState<UploadState>({ status: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setState({ status: "idle" });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setState({ status: "error", message: "No file selected", details: ["Choose a product source file before starting the import."] });
      return;
    }
    setState({ status: "loading" });
    try {
      const tokenResponse = await fetch("/auth/realms/basyx/protocol/openid-connect/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type: "password",
          client_id: "basyx-api",
          client_secret: "basyx-api-secret",
          username,
          password,
        }),
      });
      const tokenPayload = await tokenResponse.json() as { access_token?: string; error_description?: string };
      if (!tokenResponse.ok || !tokenPayload.access_token) {
        throw new ImportApiError("Authentication failed", [tokenPayload.error_description ?? "Use a valid Keycloak user account."]);
      }
      const result = await importProductFile(file, tokenPayload.access_token);
      setState({ status: "success", result });
    } catch (error) {
      if (error instanceof ImportApiError) {
        setState({ status: "error", message: error.message, details: error.details });
      } else {
        setState({ status: "error", message: "Import failed", details: ["An unexpected error occurred. Please retry."] });
      }
    }
  }

  return (
    <form className="upload-card" onSubmit={submit}>
      <div className="upload-heading"><div className="icon-tile"><Icon name="upload" /></div><div><h2>Import product data</h2><p>Authenticate as a user, then upload an AASX package.</p></div></div>
      <div className="upload-credentials">
        <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
      </div>
      <button className="file-drop" type="button" onClick={() => inputRef.current?.click()}>
        <input ref={inputRef} type="file" accept=".aasx" onChange={selectFile} hidden />
        <span className="file-icon"><Icon name="documents" /></span>
        {file ? <><strong>{file.name}</strong><span>{formatFileSize(file.size)} · Click to replace</span></> : <><strong>Choose a file</strong><span>.aasx only</span></>}
      </button>
      <div className="upload-actions">
        <p>Protected endpoint: <code>POST /upload</code></p>
        <button className="primary-button" type="submit" disabled={state.status === "loading"}>
          {state.status === "loading" ? <><span className="spinner" /> Importing…</> : <>Start import <Icon name="arrow" /></>}
        </button>
      </div>
      {state.status === "success" && <div className="notice success" role="status"><Icon name="check" /><div><strong>Import ready</strong><p>{state.result.message}</p><small>Reference: {state.result.importId}</small></div></div>}
      {state.status === "error" && <div className="notice error" role="alert"><span className="notice-symbol">!</span><div><strong>{state.message}</strong><ul>{state.details.map((detail) => <li key={detail}>{detail}</li>)}</ul></div></div>}
    </form>
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}
