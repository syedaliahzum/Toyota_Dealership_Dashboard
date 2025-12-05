"use client";

import { useRef, useState } from "react";
import { Upload, FileCheck2, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

/* ======= Types from API docs ======= */
type UploadFileInfo = {
  type: "technician_report" | "daily_report" | "rework_report";
  original_filename: string; // Corrected typo: original_filename
  saved_filename: string;
  path: string;
  size_bytes: number;
  size_kb: number;
};

type UploadResponse = {
  message: string;
  files: UploadFileInfo[];
  timestamp: string;
  pdf_directory: string;
};

/* ======= Config ======= */
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || ""; // empty for relative proxy
const UPLOAD_ENDPOINT = `${API_BASE}/api/upload-reports`; // <-- calls Next.js route now
const MAX_MB = 10;
const MAX_BYTES = MAX_MB * 1024 * 1024;

export default function UploadDailyReportPage() {
  const inputRef1 = useRef<HTMLInputElement | null>(null);
  const inputRef2 = useRef<HTMLInputElement | null>(null);
  const inputRef3 = useRef<HTMLInputElement | null>(null);

  const [file1Name, setFile1Name] = useState<string>("");
  const [file2Name, setFile2Name] = useState<string>("");
  const [file3Name, setFile3Name] = useState<string>("");

  const [error1, setError1] = useState<string>("");
  const [error2, setError2] = useState<string>("");
  const [error3, setError3] = useState<string>("");

  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string>("");
  const [successMsg, setSuccessMsg] = useState<string>("");

  function openPicker(pickerNum: 1 | 2 | 3) {
    if (pickerNum === 1) {
      setError1("");
      inputRef1.current?.click();
    } else if (pickerNum === 2) {
      setError2("");
      inputRef2.current?.click();
    } else {
      setError3("");
      inputRef3.current?.click();
    }
  }

  function validatePdf(
    file: File,
    label: "Technician Report" | "Daily Report" | "Rework Report",
    otherFiles: (File | null | undefined)[],
  ): string | null {
    const lower = file.name.toLowerCase();
    const isPdf =
      file.type === "application/pdf" || lower.endsWith(".pdf"); // strict enough for browsers that omit type

    for (const otherFile of otherFiles) {
      if (otherFile && otherFile.name === file.name && otherFile.size === file.size) {
        return `${label} validation failed: This file has already been selected for another report.`;
      }
    }

    if (!isPdf) return `${label} validation failed: Only PDF files are allowed`;

    if (file.size === 0) return `${label} validation failed: File is empty`;

    if (file.size > MAX_BYTES) {
      const mb = (file.size / (1024 * 1024)).toFixed(2);
      return `${label} size validation failed: File size (${mb}MB) exceeds maximum allowed size (${MAX_MB}MB)`;
    }
    return null;
  }

  function onPickFile(e: React.ChangeEvent<HTMLInputElement>, fileNum: 1 | 2 | 3) {
    const f = e.target.files?.[0];

    // clear peer state
    if (fileNum === 1) {
      setError1("");
      setFile1Name("");
    } else if (fileNum === 2) {
      setError2("");
      setFile2Name("");
    }
    if (fileNum === 3) {
      setError3("");
      setFile3Name("");
    }

    if (!f) return;

    const label =
      fileNum === 1 ? "Technician Report" : fileNum === 2 ? "Daily Report" : "Rework Report";
    const otherFiles: (File | undefined | null)[] = [];
    if (fileNum !== 1) otherFiles.push(inputRef1.current?.files?.[0]);
    if (fileNum !== 2) otherFiles.push(inputRef2.current?.files?.[0]);
    if (fileNum !== 3) otherFiles.push(inputRef3.current?.files?.[0]);

    const validationError = validatePdf(f, label, otherFiles);

    if (validationError) {
      if (fileNum === 1) {
        setError1(validationError);
      } else if (fileNum === 2) {
        setError2(validationError);
      } else {
        setError3(validationError);
      }
      // Clear the input so the same file can be re-selected after fixes
      e.target.value = "";
      return;
    }

    if (fileNum === 1) setFile1Name(f.name);
    else if (fileNum === 2) setFile2Name(f.name);
    else setFile3Name(f.name);
  }

  async function handleSubmit() {
    setServerError("");
    setSuccessMsg("");

    // Basic presence validation
    if (!inputRef1.current?.files?.[0] || !inputRef2.current?.files?.[0]) {
      alert("Please upload both the Technician Report and Daily Report before submitting.");
      return;
    }

    // Re-validate before sending (protects against drag/drop or browser quirks)
    const f1 = inputRef1.current.files[0];
    const f2 = inputRef2.current.files[0];

    const v1 = validatePdf(f1, "Technician Report", [f2]);
    const v2 = validatePdf(f2, "Daily Report", [f1]);
    if (v1 || v2) {
      if (v1) setError1(v1);
      if (v2) setError2(v2);
      return;
    }

    const formData = new FormData();
    formData.append("technicianreport", f1); // Key for technician report
    formData.append("dailyreport", f2); // Key for daily report
    const f3 = inputRef3.current?.files?.[0];
    if (f3) {
      formData.append("reworkreport", f3); // Key for optional rework report
    }

    setSubmitting(true);

    // Abort controller with a sensible timeout
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), 45_000);

    try {
      const res = await fetch(UPLOAD_ENDPOINT, {
        method: "POST",
        body: formData,
        signal: ac.signal,
      });

      // Try to parse JSON either way for better feedback
      let payload: any = null;
      try {
        payload = await res.json();
      } catch {
        // pass — server might have returned non-JSON on error
      }

      if (!res.ok) {
        const detail =
          payload?.detail ||
          `Upload failed with status ${res.status}${
            res.statusText ? `: ${res.statusText}` : ""
          }`;
        throw new Error(detail);
      }

      const data = payload as UploadResponse;

      // Success UI
      setSuccessMsg("PDF's Submitted successfully.");

      // Reset inputs and labels
      if (inputRef1.current) inputRef1.current.value = "";
      if (inputRef2.current) inputRef2.current.value = "";
      if (inputRef3.current) inputRef3.current.value = "";
      setFile1Name("");
      setFile2Name("");
      setFile3Name("");
    } catch (err: any) {
      if (err?.name === "AbortError") {
        setServerError("Request timed out. Please try again.");
      } else {
        setServerError(err?.message || "An unexpected error occurred.");
      }
    } finally {
      clearTimeout(timer);
      setSubmitting(false);
    }
  }

  const submitDisabled =
    submitting || !file1Name || !file2Name || Boolean(error1) || Boolean(error2) || Boolean(error3);

  return (
    <main className="min-h-screen bg-white text-zinc-900 dark:bg-[#0b0b0b] dark:text-white">
      <section className="mx-auto max-w-3xl px-4 py-12">
        {/* Heading */}
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-white">Upload Daily Reports</h1>

        {/* --- Upload Section 1 --- */}
        <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-white/10 dark:bg-[#121212]">
          <p className="text-sm text-zinc-400">
            Please upload the <span className="font-semibold text-zinc-300">Technician Report</span> as a PDF file.
          </p>

          <div className="mt-5">
            <button
              onClick={() => openPicker(1)}
              className="group inline-flex items-center gap-2 rounded-xl border border-zinc-300 bg-zinc-100 px-5 py-3 text-sm font-medium text-zinc-800 transition hover:bg-zinc-200 focus:outline-none focus:ring-2 focus:ring-red-500/60 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
              aria-describedby={error1 ? "upload-error-1" : undefined}
              disabled={submitting}
            >
              <span className="grid h-6 w-6 place-items-center rounded-lg bg-red-600/20 ring-1 ring-red-600/40 transition group-hover:bg-red-600/30">
                <Upload className="h-3.5 w-3.5" />
              </span>
              Upload Technician Report
            </button>

            <input
              ref={inputRef1}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => onPickFile(e, 1)}
            />
          </div>

          <div className="mt-4 min-h-[1.25rem]" aria-live="polite">
            {file1Name ? (
              <p className="text-sm text-zinc-300">
                Selected file: <span className="font-medium text-zinc-800 dark:text-zinc-300">{file1Name}</span>
              </p>
            ) : error1 ? (
              <p id="upload-error-1" className="inline-flex items-start gap-2 text-sm text-red-400">
                <AlertCircle className="mt-[1px] h-4 w-4 shrink-0" />
                <span>{error1}</span>
              </p>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-500">Max size: {MAX_MB}MB • Format: PDF</p>
        </div>

        {/* --- Upload Section 2 --- */}
        <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-white/10 dark:bg-[#121212]">
          <p className="text-sm text-zinc-400">
            Please upload the <span className="font-semibold text-zinc-300">Daily Report</span> as a PDF file.
          </p>

          <div className="mt-5">
            <button
              onClick={() => openPicker(2)}
              className="group inline-flex items-center gap-2 rounded-xl border border-zinc-300 bg-zinc-100 px-5 py-3 text-sm font-medium text-zinc-800 transition hover:bg-zinc-200 focus:outline-none focus:ring-2 focus:ring-red-500/60 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
              aria-describedby={error2 ? "upload-error-2" : undefined}
              disabled={submitting}
            >
              <span className="grid h-6 w-6 place-items-center rounded-lg bg-red-600/20 ring-1 ring-red-600/40 transition group-hover:bg-red-600/30">
                <Upload className="h-3.5 w-3.5" />
              </span>
              Upload Daily Report
            </button>

            <input
              ref={inputRef2}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => onPickFile(e, 2)}
            />
          </div>

          <div className="mt-4 min-h-[1.25rem]" aria-live="polite">
            {file2Name ? (
              <p className="text-sm text-zinc-300">
                Selected file: <span className="font-medium text-zinc-800 dark:text-zinc-300">{file2Name}</span>
              </p>
            ) : error2 ? (
              <p id="upload-error-2" className="inline-flex items-start gap-2 text-sm text-red-400">
                <AlertCircle className="mt-[1px] h-4 w-4 shrink-0" />
                <span>{error2}</span>
              </p>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-500">Max size: {MAX_MB}MB • Format: PDF</p>
        </div>

        {/* --- Upload Section 3 (Optional) --- */}
        <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-white/10 dark:bg-[#121212]">
          <p className="text-sm text-zinc-400">
            Please upload the <span className="font-semibold text-zinc-300">Rework Report</span> as a PDF
            file (Optional).
          </p>

          <div className="mt-5">
            <button
              onClick={() => openPicker(3)} 
              className="group inline-flex items-center gap-2 rounded-xl border border-zinc-300 bg-zinc-100 px-5 py-3 text-sm font-medium text-zinc-800 transition hover:bg-zinc-200 focus:outline-none focus:ring-2 focus:ring-red-500/60 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
              aria-describedby={error3 ? "upload-error-3" : undefined}
              disabled={submitting}
            >
              <span className="grid h-6 w-6 place-items-center rounded-lg bg-red-600/20 ring-1 ring-red-600/40 transition group-hover:bg-red-600/30">
                <Upload className="h-3.5 w-3.5" />
              </span>
              Upload Rework Report
            </button>

            <input
              ref={inputRef3}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => onPickFile(e, 3)}
            />
          </div>

          <div className="mt-4 min-h-[1.25rem]" aria-live="polite">
            {file3Name ? (
              <p className="text-sm text-zinc-300">
                Selected file: <span className="font-medium text-zinc-800 dark:text-zinc-300">{file3Name}</span>
              </p>
            ) : error3 ? (
              <p id="upload-error-3" className="inline-flex items-start gap-2 text-sm text-red-400">
                <AlertCircle className="mt-[1px] h-4 w-4 shrink-0" />
                <span>{error3}</span>
              </p>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-500">Max size: {MAX_MB}MB • Format: PDF</p>
        </div>

        {/* --- Server messages --- */}
        <div className="mt-6 space-y-3" aria-live="polite">
          {serverError && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-[2px] h-4 w-4" />
                <div>{serverError}</div>
              </div>
            </div>
          )}
          {successMsg && (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-[2px] h-4 w-4" />
                <div>{successMsg}</div>
              </div>
            </div>
          )}
        </div>

        {/* --- Submit Button --- */}
        <div className="mt-8 flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={submitDisabled}
            className="group inline-flex items-center gap-2.5 rounded-xl bg-red-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500/60 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-red-600 dark:hover:bg-red-700"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading…
              </>
            ) : (
              <>
                <FileCheck2 className="h-4 w-4" />
                Submit Reports
              </>
            )}
          </button>
        </div>
      </section>
    </main>
  );
}
