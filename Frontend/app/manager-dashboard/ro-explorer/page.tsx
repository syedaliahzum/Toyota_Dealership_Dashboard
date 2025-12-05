// app/manager-dashboard/ro-explorer/page.tsx
"use client";

import { createTheme, CssBaseline, ThemeProvider } from "@mui/material";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import React, { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Filter, X } from "lucide-react";

/* =========================
 * Types for API response
 * ========================= */

type JobRecord = {
  service_date: string; // "YYYY-MM-DD"
  chassis_no: string;
  ro_no: number;
  service_nature: string;
  receiving_date_time: string; // "YYYY-MM-DD HH:mm:ss"
  delivery_date_time: string;  // "YYYY-MM-DD HH:mm:ss"
  promised_date_time: string;  // "YYYY-MM-DD HH:mm:ss"
  technician_name: string;
  vehicle_variant: string;
};

type JobRecordsResponse = {
  success: boolean;
  filters_applied: {
    receiving_date_time: string | null;
    delivery_date_time: string | null;
    promised_date_time: string | null;
    technician_name: string | null;
  };
  no_of_rows: number;
  job_records: JobRecord[];
  total_records: number;
  timestamp: string;
};

/* =========================
 * Utilities
 * ========================= */

const fmtDate = (dateStr: string) => {
  if (!dateStr) return "";
  // API gives "YYYY-MM-DD"
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const fmtDateTime = (dateTimeStr: string) => {
  if (!dateTimeStr) return "";
  // API format "YYYY-MM-DD HH:mm:ss"
  const normalized = dateTimeStr.replace(" ", "T");
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return dateTimeStr;
  return d.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Parse a `YYYY-MM-DD` string into a Date at local midnight (safe for MUI DatePicker)
function parseYYYYMMDDToLocalDate(s: string): Date {
  const [yStr, mStr, dStr] = s.split("-");
  const y = Number(yStr);
  const m = Number(mStr) - 1;
  const d = Number(dStr);
  return new Date(y, m, d);
}

// Format a Date (local) into `YYYY-MM-DD`
function formatLocalDateToYYYYMMDD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}


const escapeCsvValue = (value: any) => {
  if (value === null || value === undefined) return "";
  let str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
};

const darkTheme = createTheme({
  palette: {
    mode: "dark",
    background: { default: "#121212", paper: "#121212" },
    text: { primary: "#e5e5e5", secondary: "#a1a1aa" },
    primary: { main: "#ef4444" },
  },
  typography: { fontFamily: "var(--font-poppins), system-ui, sans-serif" },
});

const lightTheme = createTheme({
  palette: {
    mode: "light",
    background: { default: "#ffffff", paper: "#ffffff" },
    text: { primary: "#171717", secondary: "#71717a" },
    primary: { main: "#ef4444" },
  },
  typography: { fontFamily: "var(--font-poppins), system-ui, sans-serif" },
});


/* =========================
 * Component
 * ========================= */

export default function ROExplorerPage() {
  // Staged filters for input fields
  const [technicianName, setTechnicianName] = useState<string>("");
  const [receivingDate, setReceivingDate] = useState<string>(""); // YYYY-MM-DD
  const [deliveryDate, setDeliveryDate] = useState<string>("");
  const [promisedDate, setPromisedDate] = useState<string>("");

  // Applied filters that trigger the API call
  const [appliedTechnicianName, setAppliedTechnicianName] =
    useState<string>("");
  const [appliedReceivingDate, setAppliedReceivingDate] = useState<string>("");
  const [appliedDeliveryDate, setAppliedDeliveryDate] = useState<string>("");
  const [appliedPromisedDate, setAppliedPromisedDate] = useState<string>("");

  // Data state
  const [records, setRecords] = useState<JobRecord[]>([]);
  const [noOfRows, setNoOfRows] = useState<number>(0); // from API
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Theme state
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);

  // Pagination (0–100, 101–200, ...)
  const [page, setPage] = useState<number>(1);
  const pageSize = 100; // fixed as requested (max 1000 total => 10 pages)

  // Detect theme preference on mount
  useEffect(() => {
    const darkModeMediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    setIsDarkMode(darkModeMediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setIsDarkMode(e.matches);
    };

    darkModeMediaQuery.addEventListener("change", handleChange);
    return () => darkModeMediaQuery.removeEventListener("change", handleChange);
  }, []);

  const resetFilters = () => {
    // Clear input fields
    setTechnicianName("");
    setReceivingDate("");
    setDeliveryDate("");
    setPromisedDate("");
    // Clear applied filters to trigger a refetch with no filters
    setAppliedTechnicianName("");
    setAppliedReceivingDate("");
    setAppliedDeliveryDate("");
    setAppliedPromisedDate("");
    setPage(1);
  };

  // When the apply button is clicked, copy staged filters to applied filters and go to page 1
  const handleApplyFilters = () => {
    setAppliedTechnicianName(technicianName);
    setAppliedReceivingDate(receivingDate);
    setAppliedDeliveryDate(deliveryDate);
    setAppliedPromisedDate(promisedDate);
    setPage(1);
  };

  // Fetch from our Next.js API -> FastAPI
  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      try {
        setLoading(true);
        setError(null);

        const params = new URLSearchParams();
        // Standard pagination: send page and page size to the API
        params.set("page_number", String(page));
        params.set("page_size", String(pageSize));

        if (appliedTechnicianName.trim()) {
          params.set("technician_name", appliedTechnicianName.trim());
        }
        if (appliedReceivingDate) {
          params.set("receiving_date_time", appliedReceivingDate); // YYYY-MM-DD from <input type="date">
        }
        if (appliedDeliveryDate) {
          params.set("delivery_date_time", appliedDeliveryDate);
        }
        if (appliedPromisedDate) {
          params.set("promised_date_time", appliedPromisedDate);
        }

        const res = await fetch(`/api/job-records?${params.toString()}`, {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
        });

        if (!res.ok) {
          const errJson = await res.json().catch(() => null);
          throw new Error(
            errJson?.detail ||
              `Failed to fetch job records (status ${res.status}).`,
          );
        }

        const data: JobRecordsResponse = await res.json();

        if (!data.success) {
          throw new Error(
            (data as any).detail || "API responded with success=false.",
          );
        }

        setRecords(data.job_records || []);
        setNoOfRows(data.no_of_rows || 0);
        setTotalRecords(data.total_records || 0);
      } catch (err: any) {
        if (err.name === "AbortError") return;
        console.error("Error loading job records:", err);
        setError(err.message || "Failed to load job records.");
        setRecords([]);
        setNoOfRows(0);
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    return () => controller.abort();
  }, [
    page,
    appliedTechnicianName,
    appliedReceivingDate,
    appliedDeliveryDate,
    appliedPromisedDate,
  ]);

  // Total pages based on how many records API returned
 const totalPages = useMemo(() => {
    if (totalRecords <= 0) return 1;
    return Math.max(1, Math.ceil(totalRecords / pageSize));
  }, [totalRecords, pageSize]);

  const startRow = useMemo(() => {
    if (!noOfRows) return 0;
    return (page - 1) * pageSize + 1;
  }, [page, noOfRows, pageSize]);

  const endRow = useMemo(() => {
    if (!noOfRows) return 0;
    return Math.min(page * pageSize, noOfRows);
  }, [page, noOfRows, pageSize]);

  const handleExportCsv = () => {
    if (!records.length) return;

    const headers = [
      "Row No",
      "Service Date",
      "Chassis No",
      "RO No",
      "Service Nature",
      "Receiving Date Time",
      "Delivery Date Time",
      "Promised Date Time",
      "Technician Name",
      "Vehicle Variant",
    ];

    const csvRows = records.map((row, index) => {
      const rowNo = index + 1;
      return [
        rowNo,
        row.service_date,
        row.chassis_no,
        row.ro_no,
        row.service_nature,
        row.receiving_date_time,
        row.delivery_date_time,
        row.promised_date_time,
        row.technician_name,
        row.vehicle_variant,
      ]
        .map(escapeCsvValue)
        .join(",");
    });

    const csvContent = [headers.map(escapeCsvValue).join(","), ...csvRows].join(
      "\n",
    );
    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "ro_explorer_data.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
     <main className="min-h-screen bg-white text-zinc-900 dark:bg-[#0b0b0b] dark:text-white">
      <section className="mx-auto max-w-7xl px-4 py-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-800 dark:text-white">RO Explorer</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCsv}
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-100 px-3 py-2 text-sm text-zinc-800 hover:bg-zinc-200 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
            >
              Export CSV
            </button>
            <button
              onClick={resetFilters}
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-100 px-3 py-2 text-sm text-zinc-800 hover:bg-zinc-200 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
            >
              <X className="h-4 w-4" /> Clear Filters
            </button>
          </div>
        </div>

        {/* Filters Bar - matches API filters */}
        <ThemeProvider theme={isDarkMode ? darkTheme : lightTheme}>
          <CssBaseline />
          <div className="mb-6 rounded-2xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-4 md:items-start">
                {/* Technician name (free text – API expects full string) */}
                <div>
                  <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                    Technician Name
                  </label>
                  <input
                    value={technicianName}
                    onChange={(e) => setTechnicianName(e.target.value)}
                    placeholder="e.g. John Smith"
                    className="h-[40px] w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm text-zinc-800 outline-none focus:border-zinc-500 dark:border-white/10 dark:bg-black/30 dark:text-white dark:focus:ring-red-500/60"
                  />
                </div>

                {/* Receiving date */}
                <DatePicker
                  label="Receiving Date"
                  value={receivingDate ? parseYYYYMMDDToLocalDate(receivingDate) : null}
                  onChange={(newValue: Date | null) => {
                    setReceivingDate(
                      newValue ? formatLocalDateToYYYYMMDD(newValue) : "",
                    );
                  }}
                  slotProps={{
                    textField: { fullWidth: true, size: "small" },
                  }}
                />

                {/* Delivery date */}
                <DatePicker
                  label="Delivery Date"
                  value={deliveryDate ? parseYYYYMMDDToLocalDate(deliveryDate) : null}
                  onChange={(newValue: Date | null) => {
                    setDeliveryDate(
                      newValue ? formatLocalDateToYYYYMMDD(newValue) : "",
                    );
                  }}
                  slotProps={{
                    textField: { fullWidth: true, size: "small" },
                  }}
                />

                {/* Promised date */}
                <DatePicker
                  label="Promised Date"
                  value={promisedDate ? parseYYYYMMDDToLocalDate(promisedDate) : null}
                  onChange={(newValue: Date | null) => {
                    setPromisedDate(
                      newValue ? formatLocalDateToYYYYMMDD(newValue) : "",
                    );
                  }}
                  slotProps={{
                    textField: { fullWidth: true, size: "small" },
                  }}
                />
              </div>
            </LocalizationProvider>
          </div>
        </ThemeProvider>

        {/* Apply Filters Button */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={handleApplyFilters}
            className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50 dark:bg-red-600 dark:hover:bg-red-700"
          >
            Apply Filters
          </button>
        </div>

        {/* Results + Count */}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3 text-sm text-zinc-500 dark:text-zinc-400">
          <span className="inline-flex items-center gap-2">
            <Filter className="h-4 w-4" />
            {loading ? (
              <span>Loading job records…</span>
            ) : (
              <>
                Showing{" "}
                <span className="text-zinc-800 dark:text-white">
                  {noOfRows.toLocaleString()}
                </span>{" "}
                records (from API) total records {totalRecords}
              </>
            )}
          </span>

          {/* Pagination */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading || totalRecords <= pageSize}
              className="rounded-lg border border-zinc-200 bg-zinc-100 p-1.5 text-zinc-800 disabled:opacity-40 dark:border-white/10 dark:bg-white/5 dark:text-zinc-300"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span>
              Page{" "}
              <span className="text-zinc-800 dark:text-white">
                {page} / {totalPages}
              </span>
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading || totalRecords <= pageSize}
              className="rounded-lg border border-zinc-200 bg-zinc-100 p-1.5 text-zinc-800 disabled:opacity-40 dark:border-white/10 dark:bg-white/5 dark:text-zinc-300"
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-3 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        )}

        {/* Table */}
        <div className="overflow-auto rounded-2xl border border-zinc-200 dark:border-white/10">
          <table className="min-w-[900px] w-full border-separate border-spacing-0 bg-white text-sm dark:bg-[#121212]">
            <thead className="sticky top-0 z-10 bg-zinc-50 text-zinc-600 dark:bg-[#151515] dark:text-zinc-300">
              <tr>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Row #
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Service Date
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Chassis No
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  RO No
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Service Nature
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Receiving Date Time
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Delivery Date Time
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Promised Date Time
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Technician Name
                </th>
                <th className="border-b border-zinc-200 px-3 py-2 text-left dark:border-white/10">
                  Vehicle Variant
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && !records.length && (
                <tr>
                  <td
                    colSpan={10}
                    className="px-3 py-10 text-center text-zinc-500 dark:text-zinc-400"
                  >
                    Loading...
                  </td>
                </tr>
              )}

              {!loading && records.length === 0 && (
                <tr>
                  <td
                    colSpan={10}
                    className="px-3 py-10 text-center text-zinc-500 dark:text-zinc-400"
                  >
                    No records found with current filters.
                  </td>
                </tr>
              )}

              {records.map((r, idx) => {
                const globalIndex = (page - 1) * pageSize + idx; // 0-based
                const rowNo = globalIndex + 1;
                return (
                  <tr key={`${r.ro_no}-${rowNo}`} className="hover:bg-zinc-50 dark:hover:bg-white/5">
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {rowNo}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {fmtDate(r.service_date)}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {r.chassis_no}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {r.ro_no}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {r.service_nature}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {fmtDateTime(r.receiving_date_time)}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {fmtDateTime(r.delivery_date_time)}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {fmtDateTime(r.promised_date_time)}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {r.technician_name}
                    </td>
                    <td className="border-b border-zinc-200 px-3 py-2 text-zinc-800 dark:border-white/10 dark:text-white">
                      {r.vehicle_variant}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

      </section>
    </main>
  );
}
