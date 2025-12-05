// app/manager-dashboard/service-quality/page.tsx
"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { ThemeProvider, createTheme, CssBaseline } from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LineChart } from "@mui/x-charts/LineChart";

/* -------------------- API Types -------------------- */
type ReworkByMonth = {
  month: string; // "2025-01"
  rework_count: number;
};

type ReworkRateApiResponse = {
  success: boolean;
  rework_rate: number; // 15
  first_time_fix_rate: number; // 85
  total_rework: number; // 23
  total_jobs: number; // 150
  rework_by_month: ReworkByMonth[];
  timestamp: string;
};

type ReworkByDateItem = {
  date: string; // "2024-01-01"
  rework_count: number; // 2
};

type ReworkByDateResponse = {
  success: boolean;
  date_range: {
    start_date: string;
    end_date: string;
  };
  total_days: number;
  total_rework_count: number;
  rework_data: ReworkByDateItem[];
  timestamp: string;
};

/* -------------------- Cache Key -------------------- */
const REWORK_RATE_CACHE_KEY = "reworkRateCache_v1";

/* -------------------- Small UI helpers -------------------- */
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
      className={`rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212] ${className}`}
    >
      {title && (
        <p className="mb-2 text-sm text-zinc-600 dark:text-zinc-300">
          {title}
        </p>
      )}
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
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{label}</p>
      <div className="mt-2 text-3xl font-semibold">{value}</div>
      {help && (
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{help}</p>
      )}
    </div>
  );
}

/* -------------------- Helpers -------------------- */
function formatMonthLabel(yyyymm: string): string {
  // "2025-01" → "Jan 2025"
  const [yearStr, monthStr] = yyyymm.split("-");
  const year = Number(yearStr);
  const monthIndex = Number(monthStr) - 1;
  if (Number.isNaN(year) || Number.isNaN(monthIndex)) return yyyymm;
  const d = new Date(year, monthIndex, 1);
  return d.toLocaleString(undefined, { month: "short", year: "numeric" });
}

/* -------------------- Themes -------------------- */
const darkTheme = createTheme({
  palette: {
    mode: "dark",
    background: { default: "#121212", paper: "#121212" },
    text: { primary: "#f9fafb", secondary: "#a1a1aa" },
    primary: { main: "#ef4444" },
  },
  typography: { fontFamily: "var(--font-poppins), system-ui, sans-serif" },
  components: {
    MuiInputBase: {
      styleOverrides: {
        root: {
          color: "#f9fafb",
        },
        input: {
          color: "#f9fafb",
          WebkitTextFillColor: "#f9fafb",
        },
      },
    },
  },
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

/* -------------------- Page -------------------- */
export default function ServiceQualityPage() {
  /* ===== KPI + Monthly Chart state (from /rework-rate) ===== */
  const [reworkRate, setReworkRate] = useState(0);
  const [ftfr, setFtfr] = useState(0);
  const [totalReworks, setTotalReworks] = useState(0);
  const [months, setMonths] = useState<string[]>([]);
  const [monthlyCounts, setMonthlyCounts] = useState<number[]>([]);
  const [kpiLoading, setKpiLoading] = useState(true);
  const [kpiError, setKpiError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  /* ===== Weekly Chart state (from /rework-rate-by-date) ===== */
  const [fromWeekDate, setFromWeekDate] = useState<string>("");
  const [toWeekDate, setToWeekDate] = useState<string>("");
  const [weekChartError, setWeekChartError] = useState<string>("");
  const [weeklyLoading, setWeeklyLoading] = useState(false);
  const [weeklyData, setWeeklyData] = useState<{
    labels: string[];
    data: number[];
  } | null>(null);

  /* ----------- Apply data from API or cache into state ----------- */
  const applyReworkRateDataToState = (data: ReworkRateApiResponse) => {
    setReworkRate(data.rework_rate);
    setFtfr(data.first_time_fix_rate);
    setTotalReworks(data.total_rework);

    const sorted = [...data.rework_by_month].sort((a, b) =>
      a.month.localeCompare(b.month)
    );
    setMonths(sorted.map((item) => formatMonthLabel(item.month)));
    setMonthlyCounts(sorted.map((item) => item.rework_count));
    setLastUpdated(data.timestamp || null);
  };

  /* ----------- Fetch + cache function (used by initial & Refresh) ----------- */
  const fetchAndCacheReworkRate = async () => {
    setKpiLoading(true);
    setKpiError(null);

    try {
      const res = await fetch("/api/rework-rate", {
        method: "GET",
        cache: "no-store",
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(
          `API /api/rework-rate error: ${res.status} ${res.statusText} ${text}`
        );
      }

      const data: ReworkRateApiResponse = await res.json();
      if (!data.success) {
        throw new Error("FastAPI /rework-rate returned success=false");
      }

      if (typeof window !== "undefined") {
        localStorage.setItem(REWORK_RATE_CACHE_KEY, JSON.stringify(data));
      }

      applyReworkRateDataToState(data);
    } catch (err: any) {
      console.error(err);
      setKpiError(
        err?.message || "Unable to fetch rework KPI data from the server."
      );
    } finally {
      setKpiLoading(false);
    }
  };

  /* ----------- Initial load ----------- */
  useEffect(() => {
    if (typeof window === "undefined") return;

    const cachedStr = localStorage.getItem(REWORK_RATE_CACHE_KEY);
    if (cachedStr) {
      try {
        const cached: ReworkRateApiResponse = JSON.parse(cachedStr);
        if (cached && cached.success) {
          applyReworkRateDataToState(cached);
          setKpiLoading(false);
          return;
        }
      } catch (e) {
        console.warn("Failed to parse rework-rate cache, refetching...", e);
      }
    }

    fetchAndCacheReworkRate();
  }, []);

  /* ----------- Refresh button handler ----------- */
  const handleRefreshKpi = () => {
    fetchAndCacheReworkRate();
  };

  /* ----------- Weekly chart handler ----------- */
  const handleGenerateWeeklyChart = async () => {
    setWeekChartError("");
    setWeeklyData(null);

    if (!fromWeekDate || !toWeekDate) {
      setWeekChartError("Please select both a 'From' and 'To' date.");
      return;
    }

    const from = new Date(fromWeekDate);
    const to = new Date(toWeekDate);
    const dayDiff = (to.getTime() - from.getTime()) / (1000 * 3600 * 24);

    if (dayDiff <= 0) {
      setWeekChartError("'To' date must be after 'From' date.");
      return;
    }

    if (dayDiff >= 8) {
      setWeekChartError("The date range cannot be more than 7 days.");
      return;
    }

    setWeeklyLoading(true);

    try {
      const params = new URLSearchParams({
        start_date: fromWeekDate,
        end_date: toWeekDate,
      });

      const res = await fetch(
        `/api/rework-rate-by-date?${params.toString()}`,
        {
          method: "GET",
          cache: "no-store",
        }
      );

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(
          `API /api/rework-rate-by-date error: ${res.status} ${res.statusText} ${text}`
        );
      }

      const data: ReworkByDateResponse = await res.json();
      if (!data.success) {
        throw new Error("FastAPI /rework-rate-by-date returned success=false");
      }

      const map = new Map<string, number>();
      for (const item of data.rework_data || []) {
        map.set(item.date, item.rework_count);
      }

      const labels: string[] = [];
      const dailyCounts: number[] = [];

      for (
        let d = new Date(
          Date.UTC(
            from.getUTCFullYear(),
            from.getUTCMonth(),
            from.getUTCDate()
          )
        );
        d <= to;
        d.setUTCDate(d.getUTCDate() + 1)
      ) {
        const dayKey = d.toISOString().slice(0, 10); // YYYY-MM-DD
        labels.push(dayKey);
        dailyCounts.push(map.get(dayKey) ?? 0);
      }

      setWeeklyData({
        labels,
        data: dailyCounts,
      });
    } catch (err: any) {
      console.error(err);
      setWeekChartError(
        err?.message ||
          "Unable to fetch weekly rework data from the server."
      );
    } finally {
      setWeeklyLoading(false);
    }
  };

  /* ----------- Detect Dark Mode ----------- */
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

  /* ----------- Select Theme ----------- */
  const theme = isDarkMode ? darkTheme : lightTheme;

  return (
    <main className="min-h-screen bg-white text-zinc-900 dark:bg-[#0b0b0b] dark:text-white">
      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Core Service Quality & Rework Report
            </h1>
            <p className="mt-1 text-sm text-zinc-400">
              Measures service accuracy and helps identify recurring issues.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <p className="text-xs text-zinc-500">
                Last updated:{" "}
                {new Date(lastUpdated).toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
            )}
            <button
              onClick={handleRefreshKpi}
              disabled={kpiLoading}
              aria-label="Refresh KPIs"
              className="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 bg-zinc-100 text-zinc-800 shadow-sm hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800"
            >
              <svg
                className={`h-4 w-4 ${kpiLoading ? "animate-spin" : ""}`}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 3v6h-6" />
                <path d="M3 21v-6h6" />
                <path d="M5.5 8.5A7 7 0 0 1 19 9" />
                <path d="M18.5 15.5A7 7 0 0 1 5 15" />
              </svg>
            </button>
          </div>
        </div>

        {/* ===== KPIs ===== */}
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <KPICard
            label="Rework Rate"
            value={kpiLoading ? "—" : `${reworkRate.toFixed(1)}%`}
            help="Rework Jobs / Total Jobs"
          />
          <KPICard
            label="First-Time Fix Rate (FTFR)"
            value={kpiLoading ? "—" : `${ftfr.toFixed(1)}%`}
            help="Jobs completed correctly on first visit"
          />
          <KPICard
            label="Total Reworks"
            value={kpiLoading ? "—" : totalReworks.toLocaleString()}
            help="Count of jobs with rework"
          />
        </div>

        <ThemeProvider theme={theme}>
          <CssBaseline />

          {/* ===== Monthly Line Chart ===== */}
          <div className="mt-6">
            <Card className="relative" title="Reworks by Month">
              {kpiLoading && months.length === 0 ? (
                <p className="text-xs text-zinc-500">Loading chart...</p>
              ) : kpiError ? (
                <p className="text-xs text-red-400">{kpiError}</p>
              ) : months.length > 0 ? (
                <LineChart
                  height={350}
                  margin={{ top: 10, left: 70, right: 10, bottom: 50 }}
                  xAxis={[
                    {
                      scaleType: "point",
                      data: months,
                      tickLabelInterval: () => true,
                      tickLabelStyle: theme.typography.body2 as any,
                      label: "Months",
                    },
                  ]}
                  yAxis={[
                    {
                      min: 0,
                      tickNumber: 6,
                      tickLabelStyle: theme.typography.body2 as any,
                      label: "Rework Jobs (count)",
                    },
                  ]}
                  series={[
                    {
                      id: "monthlyReworks",
                      label: "Monthly Rework Count",
                      data: monthlyCounts,
                      color: "#ef4444",
                      curve: "monotoneX",
                      showMark: true,
                      valueFormatter: (v, ctx) =>
                        `Reworks: ${v} on ${months[ctx.dataIndex]}`,
                    },
                  ]}
                  grid={{ horizontal: true, vertical: false }}
                  sx={{
                    "& .MuiChartsAxis-line": {
                      stroke:
                        theme.palette.mode === "dark"
                          ? "#4b5563"
                          : "#d4d4d8",
                    },
                    "& .MuiChartsGrid-line": {
                      stroke:
                        theme.palette.mode === "dark"
                          ? "#27272a"
                          : "#e4e4e7",
                    },
                    "& .MuiChartsAxis-tickLabel": {
                      fill: theme.palette.text.secondary,
                    },
                    "& .MuiChartsAxis-label": {
                      fill: theme.palette.text.secondary,
                    },
                    // ✅ Legend text (e.g. "Monthly Rework Count")
                    "& .MuiChartsLegend-label": {
                      fill: theme.palette.text.primary,
                    },
                    "& .MuiChartsLegend-series text": {
                      fill: theme.palette.text.primary,
                    },
                    "& .MuiChartsMarkElement-root": {
                      stroke: theme.palette.background.paper,
                      strokeWidth: 2,
                      fill: theme.palette.primary.main,
                    },
                  }}
                />
              ) : (
                <p className="text-xs text-zinc-500">No data available.</p>
              )}
            </Card>
          </div>

          {/* ===== Weekly Rework Chart ===== */}
          <div className="mt-6">
            
            <Card title="Rework Trend by Day (Selected Week)">
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:items-end">
                  
                  {/* FROM DATE */}
                  <DatePicker
                    label="From Date"
                    value={fromWeekDate ? new Date(fromWeekDate) : null}
                    onChange={(newValue: Date | null) => {
                      if (newValue) {
                        const year = newValue.getFullYear();
                        const month = String(newValue.getMonth() + 1).padStart(
                          2,
                          "0"
                        );
                        const day = String(newValue.getDate()).padStart(
                          2,
                          "0"
                        );
                        setFromWeekDate(`${year}-${month}-${day}`);
                      } else {
                        setFromWeekDate("");
                      }
                    }}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        size: "small",
                        sx: {
                          // ✅ Input text color
                          "& .MuiInputBase-input": {
                            color: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                            WebkitTextFillColor: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                          },
                          "& .MuiPickersInputBase-root": {
                            color: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                          },
                          "& .MuiPickersOutlinedInput-root": {
                            color: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                          },
                          // ✅ Label color
                          "& .MuiInputLabel-root": {
                            color: isDarkMode ? "#9ca3af" : "#4b5563",
                          },
                          "& .MuiInputLabel-root.Mui-focused": {
                            color: isDarkMode ? "#f9fafb" : "#ef4444",
                          },
                          // ✅ Outline + hover + focus
                          "& .MuiOutlinedInput-root": {
                            backgroundColor: isDarkMode
                              ? "#1a1a1a"
                              : "#ffffff",
                            "& fieldset": {
                              borderColor: isDarkMode
                                ? "#4b5563"
                                : "#e4e4e7",
                            },
                            "&:hover fieldset": {
                              borderColor: isDarkMode
                                ? "#e5e5e5"
                                : "#111827",
                            },
                            "&.Mui-focused fieldset": {
                              borderColor: "#ef4444",
                              borderWidth: 2,
                            },
                          },
                          // ✅ Calendar icon
                          "& .MuiSvgIcon-root": {
                            color: isDarkMode ? "#f9fafb" : "#6b7280",
                          },
                          "& .MuiIconButton-root": {
                            color: isDarkMode ? "#f9fafb" : "#6b7280",
                          },
                        },
                      },
                      popper: {
                        sx: {
                          "& .MuiPaper-root": {
                            backgroundColor: isDarkMode
                              ? "#1a1a1a"
                              : "#ffffff",
                            color: isDarkMode ? "#e5e5e5" : "#000000",
                          },
                          "& .MuiPickersDay-root": {
                            color: isDarkMode ? "#e5e5e5" : "#000000",
                            "&:hover": {
                              backgroundColor: isDarkMode
                                ? "#333333"
                                : "#f5f5f5",
                            },
                          },
                          "& .MuiPickersDay-root.Mui-selected": {
                            backgroundColor: "#ef4444",
                            color: "#ffffff",
                          },
                          "& .MuiPickersCalendarHeader-root": {
                            color: isDarkMode ? "#e5e5e5" : "#000000",
                          },
                        },
                      },
                    }}
                  />

                  {/* TO DATE */}
                  <DatePicker
                    label="To Date"
                    value={toWeekDate ? new Date(toWeekDate) : null}
                    onChange={(newValue: Date | null) => {
                      if (newValue) {
                        const year = newValue.getFullYear();
                        const month = String(newValue.getMonth() + 1).padStart(
                          2,
                          "0"
                        );
                        const day = String(newValue.getDate()).padStart(
                          2,
                          "0"
                        );
                        setToWeekDate(`${year}-${month}-${day}`);
                      } else {
                        setToWeekDate("");
                      }
                    }}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        size: "small",
                        sx: {
                          "& .MuiInputBase-input": {
                            color: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                            WebkitTextFillColor: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                          },
                          "& .MuiPickersInputBase-root": {
                            color: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                          },
                          "& .MuiPickersOutlinedInput-root": {
                            color: isDarkMode ? "#f9fafb !important" : "#111827 !important",
                          },
                          "& .MuiInputLabel-root": {
                            color: isDarkMode ? "#9ca3af" : "#4b5563",
                          },
                          "& .MuiInputLabel-root.Mui-focused": {
                            color: isDarkMode ? "#f9fafb" : "#ef4444",
                          },
                          "& .MuiOutlinedInput-root": {
                            backgroundColor: isDarkMode
                              ? "#1a1a1a"
                              : "#ffffff",
                            "& fieldset": {
                              borderColor: isDarkMode
                                ? "#4b5563"
                                : "#e4e4e7",
                            },
                            "&:hover fieldset": {
                              borderColor: isDarkMode
                                ? "#e5e5e5"
                                : "#111827",
                            },
                            "&.Mui-focused fieldset": {
                              borderColor: "#ef4444",
                              borderWidth: 2,
                            },
                          },
                          "& .MuiSvgIcon-root": {
                            color: isDarkMode ? "#f9fafb" : "#6b7280",
                          },
                          "& .MuiIconButton-root": {
                            color: isDarkMode ? "#f9fafb" : "#6b7280",
                          },
                        },
                      },
                      popper: {
                        sx: {
                          "& .MuiPaper-root": {
                            backgroundColor: isDarkMode
                              ? "#1a1a1a"
                              : "#ffffff",
                            color: isDarkMode ? "#e5e5e5" : "#000000",
                          },
                          "& .MuiPickersDay-root": {
                            color: isDarkMode ? "#e5e5e5" : "#000000",
                            "&:hover": {
                              backgroundColor: isDarkMode
                                ? "#333333"
                                : "#f5f5f5",
                            },
                          },
                          "& .MuiPickersDay-root.Mui-selected": {
                            backgroundColor: "#ef4444",
                            color: "#ffffff",
                          },
                          "& .MuiPickersCalendarHeader-root": {
                            color: isDarkMode ? "#e5e5e5" : "#000000",
                          },
                        },
                      },
                    }}
                  />

                  <button
                    onClick={handleGenerateWeeklyChart}
                    disabled={weeklyLoading}
                    className="rounded-lg bg-red-500 px-4 py-2 text-white transition-all hover:bg-red-600 disabled:bg-gray-500 disabled:cursor-not-allowed"
                  >
                    {weeklyLoading ? "Loading..." : "Generate Chart"}
                  </button>
                   
                </div>
<p className="mt-1 text-xs text-zinc-600 dark:text-zinc-500">Select a date range between 2 and 7 days to generate the weekly trend.</p>
                
                {weekChartError && (
                  <div className="mt-3 rounded-lg border border-red-500 bg-red-50 p-3 text-red-600 dark:border-red-400 dark:bg-red-900/20 dark:text-red-300">
                    {weekChartError}
                  </div>
                )}

                {weeklyData && (
                  <div className="mt-6">
                    <LineChart
                      height={300}
                      series={[
                        {
                          data: weeklyData.data,
                          label: "Rework Count",
                          color: "#ef4444",
                        },
                      ]}
                      xAxis={[
                        {
                          scaleType: "point",
                          data: weeklyData.labels,
                          label: "Days",
                        },
                      ]}
                      margin={{ top: 10, right: 40, bottom: 40, left: 40 }}
                    />
                  </div>
                )}
              </LocalizationProvider>
            </Card>
          </div>
        </ThemeProvider>
      </section>
    </main>
  );
}
