// app/manager-dashboard/msi-completion/page.tsx
"use client";

import * as React from "react";
import { useState, useMemo, useEffect } from "react";
import { ThemeProvider, createTheme, CssBaseline, LinearProgress } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";

/* ===================== API Types ===================== */

type PerformanceRow = {
  name: string;
  ontime: number;
  grace: number;
  late: number;
};

type MSIResponse = {
  success: boolean;
  category: string;
  most_used_operation: string;
  least_used_operation: string;
  avg_no_of_operations: number;
  performance_table: PerformanceRow[];
  timestamp: string;
};

type MostLateMSI = {
  msi: string;
  late_count: number;
  total_count: number;
  late_percentage: number;
};

type LateMSIResponse = {
  success: boolean;
  time_period: string;
  data: MostLateMSI[];
  timestamp: string;
};

type MonthlyMSIData = {
  month: string;
  on_time: number;
  grace: number;
  late: number;
  total: number;
};

type MonthlyMSIResponse = {
  success: boolean;
  category: string;
  monthly_data: MonthlyMSIData[];
  timestamp: string;
};

type Top5LateCar = {
  variant: string;
  late_count: number;
  total_count: number;
  msi: string;
};

type Top5LateCarResponse = {
  success: boolean;
  data: Top5LateCar[];
  timestamp: string;
};

/* ===================== UI helpers ===================== */

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
    <div className={`rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212] ${className}`}>
      {title && <p className="mb-2 text-sm text-black dark:text-white">{title}</p>}
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
      <div className="mt-2 text-xl font-semibold truncate text-zinc-800 dark:text-white" title={value}>
        {value}
      </div>
      {help && <p className="mt-1 text-xs text-zinc-500">{help}</p>}
    </div>
  );
}

/* ===================== Config ===================== */

// These are the categories shown in the dropdown
// and sent to /msi?category=<value>
const MSI_CATEGORIES = [
  "GR",
  "LIGHT",
  "OIL FILTER",
  "CARE",
  "SUPER LIGH",
  "MEDIUM",
  "HEAVY",
];

const theme = createTheme({
  palette: {
    mode: "dark",
    background: { default: "#ffffff", paper: "#ffffff" },
    text: { primary: "#18181b", secondary: "#71717a" },
    primary: { main: "#ef4444" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        body.dark { background-color: #0b0b0b; color: #e5e5e5 }
      `,
    },
  },
  typography: { fontFamily: "var(--font-poppins), system-ui, sans-serif" },
});

/* ===================== Page ===================== */

export default function MSICompletionPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [msiData, setMsiData] = useState<MSIResponse | null>(null);
  const [lateMSIData, setLateMSIData] = useState<MostLateMSI[]>([]);
  const [monthlyMSIData, setMonthlyMSIData] = useState<MonthlyMSIData[]>([]);
  const [top5LateCarData, setTop5LateCarData] = useState<Top5LateCar[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingLateMSI, setLoadingLateMSI] = useState<boolean>(false);
  const [loadingMonthlyMSI, setLoadingMonthlyMSI] = useState<boolean>(false);
  const [loadingTop5Cars, setLoadingTop5Cars] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [errorLateMSI, setErrorLateMSI] = useState<string | null>(null);
  const [errorMonthlyMSI, setErrorMonthlyMSI] = useState<string | null>(null);
  const [errorTop5Cars, setErrorTop5Cars] = useState<string | null>(null);

  /* -------- Fetch /msi when category changes -------- */

  useEffect(() => {
    if (!selectedCategory) {
      setMsiData(null);
      setError(null);
      return;
    }

    let ignore = false;
    const controller = new AbortController();

    const fetchMSIData = async () => {
      try {
        setLoading(true);
        setError(null);

        const baseUrl =
          process.env.NEXT_PUBLIC_API_BASE_URL || ""; // optional; you can also just use "" for same-origin

        const res = await fetch(
          `/api/msi?category=${encodeURIComponent(selectedCategory)}`,
          {
            method: "GET",
            headers: { accept: "application/json" },
            cache: "no-store",
          }
        );


        if (!res.ok) {
          let detail = "";
          try {
            const body = await res.json();
            detail = body?.detail || "";
          } catch {
            // ignore
          }
          throw new Error(detail || `Request failed with status ${res.status}`);
        }

        const json: MSIResponse = await res.json();
        if (!ignore) {
          setMsiData(json);
        }
      } catch (err: any) {
        if (ignore || err?.name === "AbortError") return;
        setError(err?.message || "Failed to fetch MSI data");
        setMsiData(null);
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    fetchMSIData();

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [selectedCategory]);

  /* -------- Fetch most late MSI (last 30 days) -------- */

  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    const fetchLateMSI = async () => {
      try {
        setLoadingLateMSI(true);
        setErrorLateMSI(null);

        const res = await fetch("/api/msi-late-last-30-days", {
          method: "GET",
          cache: "no-store",
        });

        if (!res.ok) {
          throw new Error(`Failed to fetch late MSI data: ${res.status}`);
        }

        const json: LateMSIResponse = await res.json();
        if (!ignore && json.success) {
          setLateMSIData(json.data);
        }
      } catch (err: any) {
        if (!ignore) {
          setErrorLateMSI(err?.message || "Failed to fetch late MSI data");
        }
      } finally {
        if (!ignore) {
          setLoadingLateMSI(false);
        }
      }
    };

    fetchLateMSI();

    return () => {
      ignore = true;
      controller.abort();
    };
  }, []);

  /* -------- Fetch top 5 late cars on mount -------- */

  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    const fetchTop5LateCars = async () => {
      try {
        setLoadingTop5Cars(true);
        setErrorTop5Cars(null);

        const res = await fetch("/api/top-5-late-cars", {
          method: "GET",
          cache: "no-store",
        });

        if (!res.ok) {
          throw new Error(`Failed to fetch top 5 late cars: ${res.status}`);
        }

        const json: Top5LateCarResponse = await res.json();
        if (!ignore && json.success) {
          setTop5LateCarData(json.data);
        }
      } catch (err: any) {
        if (!ignore) {
          setErrorTop5Cars(err?.message || "Failed to fetch top 5 late cars");
        }
      } finally {
        if (!ignore) {
          setLoadingTop5Cars(false);
        }
      }
    };

    fetchTop5LateCars();

    return () => {
      ignore = true;
      controller.abort();
    };
  }, []);

  /* -------- Fetch monthly MSI data when category changes -------- */

  useEffect(() => {
    if (!selectedCategory) {
      setMonthlyMSIData([]);
      setErrorMonthlyMSI(null);
      return;
    }

    let ignore = false;
    const controller = new AbortController();

    const fetchMonthlyMSI = async () => {
      try {
        setLoadingMonthlyMSI(true);
        setErrorMonthlyMSI(null);

        const res = await fetch(
          `/api/msi-monthly?category=${encodeURIComponent(selectedCategory)}`,
          {
            method: "GET",
            cache: "no-store",
          }
        );

        if (!res.ok) {
          throw new Error(`Failed to fetch monthly MSI data: ${res.status}`);
        }

        const json: MonthlyMSIResponse = await res.json();
        if (!ignore && json.success) {
          setMonthlyMSIData(json.monthly_data);
        }
      } catch (err: any) {
        if (!ignore) {
          setErrorMonthlyMSI(err?.message || "Failed to fetch monthly MSI data");
        }
      } finally {
        if (!ignore) {
          setLoadingMonthlyMSI(false);
        }
      }
    };

    fetchMonthlyMSI();

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [selectedCategory]);

  /* -------- Prepare bar chart data from API -------- */

  const barChartData = useMemo(() => {
    if (!msiData) return null;

    const labels = msiData.performance_table.map((row) => row.name);
    const onTimeData = msiData.performance_table.map((row) => row.ontime);
    const graceData = msiData.performance_table.map((row) => row.grace);
    const lateData = msiData.performance_table.map((row) => row.late);

    return {
      labels,
      data: {
        onTime: onTimeData,
        grace: graceData,
        late: lateData,
      },
    };
  }, [msiData]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <main className="min-h-screen bg-white text-zinc-900 dark:bg-[#0b0b0b] dark:text-white">
        <section className="mx-auto max-w-7xl px-4 py-8">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-800 dark:text-white">
            MSI Completion Overview
          </h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Select an MSI category to analyze operations performance.
          </p>

          {/* TOP ROW: Late Cars Count and Late MSI Count */}
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-2">
            {/* Top 5 Late Cars Card */}
            {loadingTop5Cars ? (
              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Late Cars Count (Top 5)</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">Loading...</p>
              </div>
            ) : errorTop5Cars ? (
              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Late Cars Count (Top 5)</p>
                <p className="text-xs text-red-400 mt-2">Error: {errorTop5Cars}</p>
              </div>
            ) : (
              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Late Cars Count (Top 5)</p>
                <div className="mt-3">
                  {top5LateCarData.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-zinc-200 dark:border-white/10">
                            <th className="px-2 py-2 text-left text-zinc-600 dark:text-zinc-300">Variant</th>
                            <th className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">Late</th>
                            <th className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">Total</th>
                            <th className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">%</th>
                          </tr>
                        </thead>
                        <tbody>
                          {top5LateCarData.slice(0, 5).map((car, idx) => {
                            const percentage = car.total_count > 0 ? ((car.late_count / car.total_count) * 100).toFixed(1) : '0.0';
                            return (
                              <tr key={idx} className="border-b border-white/5 bg-white/[0.02] hover:bg-white/[0.05]">
                                <td className="px-2 py-2 text-zinc-800 dark:text-zinc-100">{car.variant}</td>
                                <td className="px-2 py-2 text-right text-red-400 font-semibold">{car.late_count}</td>
                                <td className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">{car.total_count}</td>
                                <td className="px-2 py-2 text-right text-orange-400">{percentage}%</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">No late cars found</p>
                  )}
                </div>
              </div>
            )}

            {/* Late MSI Count Card */}
            {loadingLateMSI ? (
              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Most Late MSI Categories</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">Loading...</p>
              </div>
            ) : errorLateMSI ? (
              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Most Late MSI Categories</p>
                <p className="text-xs text-red-400 mt-2">Error: {errorLateMSI}</p>
              </div>
            ) : (
              <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-white/10 dark:bg-[#121212]">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">Most Late MSI Categories</p>
                <div className="mt-3">
                  {lateMSIData.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-zinc-200 dark:border-white/10">
                            <th className="px-2 py-2 text-left text-zinc-600 dark:text-zinc-300">MSI</th>
                            <th className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">Late</th>
                            <th className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">Total</th>
                            <th className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">%</th>
                          </tr>
                        </thead>
                        <tbody>
                          {lateMSIData.slice(0, 5).map((item, idx) => (
                            <tr key={idx} className="border-b border-zinc-100 dark:border-white/5 bg-zinc-50 dark:bg-white/[0.02] hover:bg-zinc-100 dark:hover:bg-white/[0.05]">
                              <td className="px-2 py-2 text-zinc-800 dark:text-zinc-100">{item.msi}</td>
                              <td className="px-2 py-2 text-right text-red-400 font-semibold">{item.late_count}</td>
                              <td className="px-2 py-2 text-right text-zinc-600 dark:text-zinc-300">{item.total_count}</td>
                              <td className="px-2 py-2 text-right text-orange-400">{item.late_percentage.toFixed(1)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">No data available</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* MSI Category Selection and Graph */}
          <div className="mt-6">
            <Card title="Select MSI Category">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm text-zinc-800 outline-none focus:border-zinc-500 dark:border-white/10 dark:bg-[#0b0b0b] dark:text-white dark:focus:border-zinc-400"
                aria-label="Select MSI category"
              >
                <option value="">-- Choose MSI Category --</option>
                {MSI_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>

              {loading && (
                <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
                  Loading MSI data for{" "}
                  <span className="font-semibold">{selectedCategory}</span>...
                </p>
              )}

              {error && (
                <p className="mt-2 text-xs text-red-400">Error: {error}</p>
              )}
            </Card>
          </div>

          {/* KPIs: Most Used, Least Used, Average Operations */}
          {msiData && !loading && !error && (
            <div className="mt-6 grid gap-4 md:grid-cols-3 lg:grid-cols-3">
              <KPICard
                label="Most Used Operation"
                value={msiData.most_used_operation || "N/A"}
                help="Operation used the most in this category"
              />
              <KPICard
                label="Least Used Operation"
                value={msiData.least_used_operation || "N/A"}
                help="Operation used the least in this category"
              />
              <KPICard
                label="Avg No. of Operations Used"
                value={msiData.avg_no_of_operations?.toString() || "0"}
                help="Average operations performed in this category"
              />
            </div>
          )}

          {/* Bar Chart: Operations Completed On-time, Grace, Late */}
          {barChartData && !loading && !error && (
            <div className="mt-6">
              <Card title="Operations Breakdown">
                <div className="w-full overflow-x-auto pb-2">
                  <BarChart
                    height={320}
                    xAxis={[
                      {
                        scaleType: "band",
                        data: barChartData.labels,
                      },
                    ]}
                    series={[
                      {
                        data: barChartData.data.onTime,
                        label: "On Time",
                        color: "#22c55e",
                      },
                      {
                        data: barChartData.data.grace,
                        label: "Grace Time",
                        color: "#f59e0b",
                      },
                      {
                        data: barChartData.data.late,
                        label: "Late",
                        color: "#ef4444",
                      },
                    ]}
                    yAxis={[{ label: "No. of Operations" }]}
                    grid={{ horizontal: true }}
                    sx={{
                      "& .MuiChartsLegend-root": { color: "#e5e5e5" },
                      "& .MuiChartsGrid-line": { stroke: "#2a2a2a" },
                      "& .MuiChartsAxis-tickLabel tspan": {
                        fill: "#e5e5e5",
                      },
                    }}
                  />
                </div>
              </Card>
            </div>
          )}

          {/* Monthly MSI Data */}
          {selectedCategory && (
            <div className="mt-6">
              <Card title={`Monthly Data - ${selectedCategory}`}>
                {loadingMonthlyMSI ? (
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Loading...</p>
                ) : errorMonthlyMSI ? (
                  <p className="text-xs text-red-400">Error: {errorMonthlyMSI}</p>
                ) : monthlyMSIData.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-200 dark:border-white/10">
                          <th className="px-4 py-2 text-left text-zinc-600 dark:text-zinc-300">Month</th>
                          <th className="px-4 py-2 text-right text-zinc-600 dark:text-zinc-300">On Time</th>
                          <th className="px-4 py-2 text-right text-zinc-600 dark:text-zinc-300">Grace</th>
                          <th className="px-4 py-2 text-right text-zinc-600 dark:text-zinc-300">Late</th>
                          <th className="px-4 py-2 text-right text-zinc-600 dark:text-zinc-300">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {monthlyMSIData.map((item, idx) => (
                          <tr key={idx} className="border-b border-zinc-100 dark:border-white/5 hover:bg-zinc-50 dark:hover:bg-white/5">
                            <td className="px-4 py-2 text-zinc-800 dark:text-zinc-100">{item.month}</td>
                            <td className="px-4 py-2 text-right text-green-400">{item.on_time}</td>
                            <td className="px-4 py-2 text-right text-amber-400">{item.grace}</td>
                            <td className="px-4 py-2 text-right text-red-400">{item.late}</td>
                            <td className="px-4 py-2 text-right text-zinc-700 dark:text-zinc-300 font-semibold">{item.total}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">No data available for this category</p>
                )}
              </Card>
            </div>
          )}
        </section>
      </main>
    </ThemeProvider>
  );
}
