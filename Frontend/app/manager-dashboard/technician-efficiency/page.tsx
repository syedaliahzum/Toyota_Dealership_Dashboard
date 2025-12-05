// app/manager-dashboard/technician-efficiency/page.tsx
"use client";

import * as React from "react";
import { useMemo, useState, useEffect, useCallback } from "react";
import { ThemeProvider, createTheme, CssBaseline, TextField } from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { BarChart } from "@mui/x-charts/BarChart";

/* ========================= Types ========================= */

// Shape returned by API 1 now:
type JobsOverviewRow = {
  position: number;
  technician: string;
  efficiency_percent: number;
  on_time: number;
  total_jobs: number;
};

type JobsOverviewResponse = {
  success: boolean;
  num_total_jobs: number;
  total_technicians: number;
  job_data: JobsOverviewRow[];
  timestamp: string;
};

type TechnicianPerformanceResponse = {
  success: boolean;
  technician_name: string;
  date_range: {
    start_date: string;
    end_date: string;
  };
  late_jobs: number;
  ontime_jobs: number;
  grace_jobs: number;
  total_jobs: number;
  timestamp: string;
};

type TechPerformance = {
  name: string;
  late: number;
  onTime: number;
  grace: number;
  total: number;
};

type RankingRow = {
  tech: string;
  effPct: number;
  onTime: number;
  total: number;
  position: number;
};

/* ========================= UI helpers ========================= */
function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212] ${className}`}
    >
      {title && <p className="mb-2 text-sm text-gray-700 dark:text-zinc-300">{title}</p>}
      {children}
    </div>
  );
}

function KPICard({
  label,
  value,
  help,
}: {
  label: string;
  value: string;
  help?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
      <p className="text-sm text-gray-600 dark:text-zinc-400">{label}</p>
      <div className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">{value}</div>
      {help && <p className="mt-1 text-xs text-gray-500 dark:text-zinc-500">{help}</p>}
    </div>
  );
}

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

function ordinal(n: number) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

// Parse a `YYYY-MM-DD` string into a Date at local midnight (safe to pass to MUI DatePicker)
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

// Parse a `YYYY-MM-DD` string into a Date at UTC midnight (if needed for arithmetic)
function parseYYYYMMDDToUTCDate(s: string): Date {
  const [yStr, mStr, dStr] = s.split("-");
  const y = Number(yStr);
  const m = Number(mStr) - 1;
  const d = Number(dStr);
  return new Date(Date.UTC(y, m, d));
}

const OVERVIEW_CACHE_KEY = "tech_efficiency_jobs_overview_v1";

/* ========================= Page ========================= */
export default function TechnicianEfficiencyPage() {
  // Theme state
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);

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

  /** ====== OVERVIEW (API 1: /jobs-overview) ====== */
  const [totalJobs, setTotalJobs] = useState<number | null>(null);
  const [totalTechs, setTotalTechs] = useState<number | null>(null);
  const [overviewRows, setOverviewRows] = useState<JobsOverviewRow[]>([]);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // helper to apply overview data to state
  const applyOverview = useCallback((data: JobsOverviewResponse) => {
    setTotalJobs(data.num_total_jobs);
    setTotalTechs(data.total_technicians);
    setOverviewRows(data.job_data || []);
    if (data.timestamp) setLastUpdated(data.timestamp);
  }, []);

  // Refresh function: ALWAYS hits API and updates cache
  const refreshOverview = useCallback(async () => {
    try {
      setOverviewLoading(true);
      setOverviewError(null);

      const res = await fetch("/api/jobs-overview", { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`Failed to fetch jobs overview (status ${res.status})`);
      }

      const data: JobsOverviewResponse = await res.json();
      if (!data.success) {
        throw new Error("API returned success = false for jobs overview");
      }

      applyOverview(data);

      // store in localStorage cache for future mounts / tab switches
      if (typeof window !== "undefined") {
        localStorage.setItem(OVERVIEW_CACHE_KEY, JSON.stringify(data));
      }
    } catch (err: any) {
      setOverviewError(err?.message || "Failed to fetch jobs overview");
    } finally {
      setOverviewLoading(false);
    }
  }, [applyOverview]);

  // On first mount: try cache first; if no cache, call API once
  useEffect(() => {
    let didUseCache = false;

    if (typeof window !== "undefined") {
      try {
        const cachedStr = localStorage.getItem(OVERVIEW_CACHE_KEY);
        if (cachedStr) {
          const cached: JobsOverviewResponse = JSON.parse(cachedStr);
          if (cached && cached.success && Array.isArray(cached.job_data)) {
            applyOverview(cached);
            didUseCache = true;
          }
        }
      } catch {
        // ignore cache errors
      }
    }

    if (!didUseCache) {
      void refreshOverview();
    }
  }, [applyOverview, refreshOverview]);

  /** ====== Efficiency Ranking — Overall (All Time) (directly from API1) ====== */
  const overallRanking: RankingRow[] = useMemo(() => {
    if (!overviewRows.length) return [];

    const mapped = overviewRows.map((row) => ({
      tech: row.technician,
      effPct: row.efficiency_percent,
      onTime: row.on_time,
      total: row.total_jobs,
      position: row.position,
    }));

    mapped.sort((a, b) => a.position - b.position);
    return mapped;
  }, [overviewRows]);

  /** ====== Technician dropdown options (from ranking technicians) ====== */
  const techOptions = useMemo(
    () => overallRanking.map((r) => r.tech),
    [overallRanking]
  );

  /** ====== FILTERS ====== */
  const [selectedTech, setSelectedTech] = useState<string>("");
  const [fromDate, setFromDate] = useState<string>(""); // yyyy-mm-dd
  const [toDate, setToDate] = useState<string>(""); // yyyy-mm-dd

  /** ====== DATE NORMALIZATION ====== */
  const normalizedFrom = useMemo(() => {
    if (!fromDate && !toDate) return "";
    if (fromDate && toDate) {
      return fromDate <= toDate ? fromDate : toDate;
    }
    return fromDate || toDate || "";
  }, [fromDate, toDate]);

  const normalizedTo = useMemo(() => {
    if (!fromDate && !toDate) return "";
    if (fromDate && toDate) {
      return fromDate <= toDate ? toDate : fromDate;
    }
    return fromDate || toDate || "";
  }, [fromDate, toDate]);

  const hasAnyDate = !!(fromDate || toDate);
  const hasRangeForApi = !!(normalizedFrom && normalizedTo);

  const effectiveFrom = normalizedFrom;
  const effectiveTo = normalizedTo;
  const isSingleDay = !!effectiveFrom && effectiveFrom === effectiveTo;

  /** ====== Technician Performance (API 2) ====== */
  const [techPerformance, setTechPerformance] = useState<TechPerformance | null>(
    null
  );
  const [perfLoading, setPerfLoading] = useState(false);
  const [perfError, setPerfError] = useState<string | null>(null);

  const handleGenerateReport = useCallback(async () => {
    if (!selectedTech || !hasRangeForApi) {
      setTechPerformance(null);
      setPerfError(null);
      return;
    }

    try {
      setPerfLoading(true);
      setPerfError(null);
      setTechPerformance(null); // Clear previous results

      const params = new URLSearchParams({
        name: selectedTech,
        start_date: normalizedFrom,
        end_date: normalizedTo,
      });

      const res = await fetch(
        `/api/technician-performance?${params.toString()}`,
        {
          cache: "no-store",
        }
      );
      if (!res.ok) {
        throw new Error(
          `Failed to fetch technician performance (status ${res.status}) for ${selectedTech}`
        );
      }

      const data: TechnicianPerformanceResponse = await res.json();
      if (!data.success) {
        throw new Error("API returned success = false for technician performance");
      }

      setTechPerformance({
        name: data.technician_name || selectedTech,
        late: data.late_jobs,
        onTime: data.ontime_jobs,
        grace: data.grace_jobs,
        total: data.total_jobs,
      });
    } catch (err: any) {
      setPerfError(err?.message || "Failed to fetch technician performance");
    } finally {
      setPerfLoading(false);
    }
  }, [selectedTech, hasRangeForApi, normalizedFrom, normalizedTo]);

  const selectedSeries = useMemo(() => {
    if (!techPerformance) return null;
    return {
      labels: [techPerformance.name],
      data: {
        total: [techPerformance.total],
        onTime: [techPerformance.onTime],
        grace: [techPerformance.grace],
        late: [techPerformance.late],
      },
    };
  }, [techPerformance]);

  return (
     <main className="min-h-screen bg-white text-gray-900 dark:bg-[#0b0b0b] dark:text-white">
      <section className="mx-auto max-w-7xl px-4 py-8">
        {/* Header with small refresh icon on the right */}
        <div className="mb-2 flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Technician Efficiency
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-zinc-400">
              Analyze technician performance, on-time rates, and overall
              ranking.
            </p>
          </div>
          <div className="mt-1 flex flex-shrink-0 items-center gap-3">
            {lastUpdated && !overviewLoading && (
              <p className="text-right text-xs text-gray-500 dark:text-zinc-500">
                Last updated:
                <br />
                {new Date(lastUpdated).toLocaleString()}
              </p>
            )}
            <button
              onClick={refreshOverview}
              disabled={overviewLoading}
              aria-label="Refresh overview"
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-gray-300 bg-gray-100 text-gray-700 shadow-sm hover:bg-gray-200 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <svg
                className={`h-4 w-4 ${overviewLoading ? "animate-spin" : ""}`}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {/* simple refresh icon */}
                <path d="M21 3v6h-6" />
                <path d="M3 21v-6h6" />
                <path d="M5.5 8.5A7 7 0 0 1 19 9" />
                <path d="M18.5 15.5A7 7 0 0 1 5 15" />
              </svg>
            </button>
          </div>
        </div>

        {/* ===== KPIs (from API1 / cache) ===== */}
        <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <KPICard
            label="Total No. of Jobs"
            value={
              overviewLoading && totalJobs === null
                ? "Loading..."
                : overviewError
                ? "—"
                : totalJobs !== null
                ? `${totalJobs}`
                : "—"
            }
            help={
              overviewError ||
              "Overall (all time, from Jobs Overview API / cache)"
            }
          />
          <KPICard
            label="Total No. of Technicians"
            value=
            {overviewLoading && totalTechs === null
                ? "Loading..."
                : overviewError
                ? "—"
                : totalTechs !== null
                ? `${totalTechs}`
                : "—"
            }
            help={
              overviewError ||
              "Overall (all time, from Jobs Overview API / cache)"
            }
          />
          {/* placeholders */}
          <div className="hidden md:block">
            <div className="rounded-xl border border-white/0 bg-transparent p-4" />
          </div>
          <div className="hidden lg:block">
            <div className="rounded-xl border border-white/0 bg-transparent p-4" />
          </div>
        </div>

        <ThemeProvider theme={isDarkMode ? darkTheme : lightTheme}>
          <CssBaseline />
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <div className="grid gap-4 md:grid-cols-3 md:items-start">
              <div>
                <p className="mb-1 text-xs text-gray-600 dark:text-zinc-400">Select Technician</p>
                <select
                  value={selectedTech}
                  onChange={(e) => setSelectedTech(e.target.value)}
                  className="h-[40px] w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-[#0b0b0b] dark:text-white dark:focus:border-zinc-400"
                  disabled={
                    overviewLoading || !!overviewError || techOptions.length === 0
                  }
                >
                  <option value="">-- Choose Technician --</option>
                  {techOptions.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                {overviewError && (
                  <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                    Failed to load technicians from Jobs Overview API.
                  </p>
                )}
              </div>

              <DatePicker
                label="From Date"
                value={fromDate ? parseYYYYMMDDToLocalDate(fromDate) : null}
                onChange={(newValue: Date | null) => {
                  setFromDate(newValue ? formatLocalDateToYYYYMMDD(newValue) : "");
                }}
                slotProps={{
                  textField: { 
                    fullWidth: true, 
                    size: "small",
                    sx: {
                      "& .MuiOutlinedInput-root": {
                        color: "#1f2937",
                        backgroundColor: "#ffffff",
                        "& fieldset": {
                          borderColor: "#6b7280 !important",
                          borderWidth: "1.5px !important",
                        },
                        "&:hover fieldset": {
                          borderColor: "#374151 !important",
                          borderWidth: "1.5px !important",
                        },
                        "&.Mui-focused fieldset": {
                          borderColor: "#3b82f6 !important",
                          borderWidth: "2px !important",
                        },
                        "@media (prefers-color-scheme: dark)": {
                          color: "#ffffff",
                          backgroundColor: "#0b0b0b",
                          "& fieldset": {
                            borderColor: "#404040 !important",
                            borderWidth: "1px !important",
                          },
                          "&:hover fieldset": {
                            borderColor: "#525252 !important",
                            borderWidth: "1px !important",
                          },
                          "&.Mui-focused fieldset": {
                            borderColor: "#a1a1aa !important",
                            borderWidth: "1px !important",
                          },
                        },
                      },
                      "& .MuiOutlinedInput-input": {
                        color: "#1f2937",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#ffffff",
                        },
                      },
                      "& .MuiInputBase-input::placeholder": {
                        color: "#9ca3af",
                        opacity: 1,
                        "@media (prefers-color-scheme: dark)": {
                          color: "#6b7280",
                        },
                      },
                      "& .MuiInputAdornment-positionEnd .MuiIconButton-root": {
                        color: "#1f2937",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#a1a1aa",
                        },
                      },
                      "& .MuiInputAdornment-positionEnd .MuiIconButton-root svg": {
                        color: "#1f2937",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#a1a1aa",
                        },
                      },
                      "& .MuiFormLabel-root": {
                        color: "#6b7280",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#9ca3af",
                        },
                      },
                      "& .MuiFormLabel-root.Mui-focused": {
                        color: "#3b82f6",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#a1a1aa",
                        },
                      },
                    }
                  },
                }}
              />

              <DatePicker
                label="To Date"
                value={toDate ? parseYYYYMMDDToLocalDate(toDate) : null}
                onChange={(newValue: Date | null) => {
                  setToDate(newValue ? formatLocalDateToYYYYMMDD(newValue) : "");
                }}
                slotProps={{
                  textField: { 
                    fullWidth: true, 
                    size: "small",
                    sx: {
                      "& .MuiOutlinedInput-root": {
                        color: "#1f2937",
                        backgroundColor: "#ffffff",
                        "& fieldset": {
                          borderColor: "#6b7280 !important",
                          borderWidth: "1.5px !important",
                        },
                        "&:hover fieldset": {
                          borderColor: "#374151 !important",
                          borderWidth: "1.5px !important",
                        },
                        "&.Mui-focused fieldset": {
                          borderColor: "#3b82f6 !important",
                          borderWidth: "2px !important",
                        },
                        "@media (prefers-color-scheme: dark)": {
                          color: "#ffffff",
                          backgroundColor: "#0b0b0b",
                          "& fieldset": {
                            borderColor: "#404040 !important",
                            borderWidth: "1px !important",
                          },
                          "&:hover fieldset": {
                            borderColor: "#525252 !important",
                            borderWidth: "1px !important",
                          },
                          "&.Mui-focused fieldset": {
                            borderColor: "#a1a1aa !important",
                            borderWidth: "1px !important",
                          },
                        },
                      },
                      "& .MuiOutlinedInput-input": {
                        color: "#1f2937",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#ffffff",
                        },
                      },
                      "& .MuiInputBase-input::placeholder": {
                        color: "#9ca3af",
                        opacity: 1,
                        "@media (prefers-color-scheme: dark)": {
                          color: "#6b7280",
                        },
                      },
                      "& .MuiInputAdornment-positionEnd .MuiIconButton-root": {
                        color: "#1f2937",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#a1a1aa",
                        },
                      },
                      "& .MuiInputAdornment-positionEnd .MuiIconButton-root svg": {
                        color: "#1f2937",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#a1a1aa",
                        },
                      },
                      "& .MuiFormLabel-root": {
                        color: "#6b7280",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#9ca3af",
                        },
                      },
                      "& .MuiFormLabel-root.Mui-focused": {
                        color: "#3b82f6",
                        "@media (prefers-color-scheme: dark)": {
                          color: "#a1a1aa",
                        },
                      },
                    }
                  },
                }}
              />
            </div>
          </LocalizationProvider>

          <div className="mt-4 flex justify-end">
            <button
              onClick={handleGenerateReport}
              disabled={!selectedTech || !hasAnyDate || perfLoading}
              className="inline-flex items-center justify-center rounded-lg border border-red-600 bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-red-500 disabled:text-white dark:disabled:bg-red-500 dark:disabled:text-white"
            >
              {perfLoading ? (
                <>
                  <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  Generating...
                </>
              ) : "Generate"}
            </button>
          </div>

          
        </div>
          {/* ===== Technician Bar Graph (API 2) ===== */}
        <div className="mt-6">
            <Card title="Jobs Breakdown (Selected Technician)">
              {!techPerformance && !perfLoading && !perfError ? (
                <div className="py-12 text-center text-sm text-gray-600 dark:text-zinc-400">
                  Select a technician, a date range, and click "Generate" to
                  view the chart.
                </div>
              ) : perfLoading ? (
                <div className="py-12 text-center text-sm text-gray-600 dark:text-zinc-400">
                  Fetching technician performance from API…
                </div>
              ) : perfError ? (
                <div className="py-12 text-center text-sm text-red-600 dark:text-red-400">
                  {perfError || "Failed to load technician performance."}
                </div>
              ) : !techPerformance || techPerformance.total === 0 ? (
                <div className="py-12 text-center text-sm text-gray-600 dark:text-zinc-400">
                  No jobs found for{" "}
                  <span className="font-medium text-gray-800 dark:text-white">{selectedTech}</span> in the
                  selected date range.
                </div>
              ) : (
                <>
                  <BarChart
                    height={320}
                    xAxis={[
                      {
                        scaleType: "band",
                        data: selectedSeries?.labels || [],
                      },
                    ]}
                    series={[
                      {
                        data: selectedSeries?.data.total || [],
                        label: "Total Jobs",
                        color: "#94a3b8",
                      },
                      {
                        data: selectedSeries?.data.onTime || [],
                        label: "On Time",
                        color: "#22c55e",
                      },
                      {
                        data: selectedSeries?.data.grace || [],
                        label: "Grace",
                        color: "#f59e0b",
                      },
                      {
                        data: selectedSeries?.data.late || [],
                        label: "Late",
                        color: "#ef4444",
                      },
                    ]}
                    yAxis={[{ label: "No. of Jobs" }]}
                    grid={{ horizontal: true }}
                    sx={{
                      "& .MuiChartsLegend-root": { color: "#1f2937" },
                      "& .MuiChartsGrid-line": { stroke: "#e5e7eb" },
                      "& .MuiChartsAxis-tickLabel tspan": {
                        fill: "#1f2937",
                      },
                      "@media (prefers-color-scheme: dark)": {
                        "& .MuiChartsLegend-root": { color: "#e5e5e5" },
                        "& .MuiChartsGrid-line": { stroke: "#2a2a2a" },
                        "& .MuiChartsAxis-tickLabel tspan": {
                          fill: "#e5e5e5",
                        },
                      },
                    }}
                  />
                  <p className="mt-2 text-xs text-gray-600 dark:text-zinc-400">
                    {isSingleDay ? (
                      <>
                        Date:{" "}
                        <span className="text-gray-900 dark:text-zinc-200">
                          {effectiveFrom || "—"}
                        </span>
                      </>
                    ) : (
                      <>
                        Range:{" "}
                        <span className="text-gray-900 dark:text-zinc-200">
                          {effectiveFrom || "—"} to {effectiveTo || "—"}
                        </span>
                      </>
                    )}{" "}
                    · Counts are returned directly by the Technician
                    Performance API.
                  </p>
                </>
              )}
            </Card>
          </div>

          {/* ===== Efficiency Ranking (from API1 / cache) ===== */}
          <div className="mt-6">
            <Card title="Efficiency Ranking — Overall (All Time)">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-gray-600 dark:text-zinc-400">
                    <tr className="border-b border-gray-200 dark:border-white/10">
                      <th className="py-2 pr-3">Position</th>
                      <th className="py-2 pr-3">Technician</th>
                      <th className="py-2 pr-3">Efficiency %</th>
                      <th className="py-2 pr-3">On Time</th>
                      <th className="py-2 pr-3">Total Jobs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overviewLoading && !overviewRows.length ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="py-6 text-center text-gray-600 dark:text-zinc-400"
                        >
                          Loading ranking data…
                        </td>
                      </tr>
                    ) : overviewError ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="py-6 text-center text-red-600 dark:text-red-400"
                        >
                          {overviewError}
                        </td>
                      </tr>
                    ) : overallRanking.length === 0 ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="py-6 text-center text-gray-600 dark:text-zinc-400"
                        >
                          No data available.
                        </td>
                      </tr>
                    ) : (
                      overallRanking.map((r) => {
                        const position = r.position;
                        const is1 = position === 1;
                        const is2 = position === 2;
                        const is3 = position === 3;

                        const rowHighlight = is1
                          ? "bg-yellow-500/10 ring-1 ring-yellow-500/30"
                          : is2
                          ? "bg-zinc-500/10 ring-1 ring-zinc-500/30"
                          : is3
                          ? "bg-amber-700/10 ring-1 ring-amber-700/30"
                          : "";

                        const medal = is1
                          ? "🥇"
                          : is2
                          ? "🥈"
                          : is3
                          ? "🥉"
                          : "";
                        const posText = is1
                          ? "1st"
                          : is2
                          ? "2nd"
                          : is3
                          ? "3rd"
                          : ordinal(position);

                        return (
                          <tr
                            key={r.tech}
                            className={`border-b border-gray-200 dark:border-white/10 ${rowHighlight}`}
                          >
                            <td className="py-2 pr-3 font-medium">
                              {medal ? `${medal} ${posText}` : posText}
                            </td>
                            <td className="py-2 pr-3">{r.tech}</td>
                            <td className="py-2 pr-3 font-medium">
                              {r.effPct.toFixed(1)}%
                            </td>
                            <td className="py-2 pr-3">{r.onTime}</td>
                            <td className="py-2 pr-3">{r.total}</td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-gray-600 dark:text-zinc-400">
                Ranking is taken from Jobs Overview API and cached locally.
                Click the refresh icon to reload from server.
              </p>
            </Card>
          </div>
        </ThemeProvider>
      </section>
    </main>
  );
}
