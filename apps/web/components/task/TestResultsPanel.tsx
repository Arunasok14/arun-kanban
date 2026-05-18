"use client";

interface TestResults {
  passed: number;
  failed: number;
  errors: number;
  details: string[];
}

interface TestResultsPanelProps {
  results: TestResults | null;
}

export function TestResultsPanel({ results }: TestResultsPanelProps) {
  if (!results) return null;

  const { passed, failed, errors, details } = results;
  const total = passed + failed + errors;
  const allPassed = failed === 0 && errors === 0 && total > 0;

  return (
    <div className={`rounded-lg border p-3 space-y-2 ${allPassed ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Test Results</span>
        {allPassed ? (
          <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
            All passing
          </span>
        ) : (
          <span className="text-xs font-medium text-red-700 bg-red-100 px-2 py-0.5 rounded-full">
            {failed + errors} failing
          </span>
        )}
      </div>

      <div className="flex gap-3 text-xs">
        <span className="text-green-700 font-medium">✓ {passed} passed</span>
        {failed > 0 && <span className="text-red-700 font-medium">✗ {failed} failed</span>}
        {errors > 0 && <span className="text-red-700 font-medium">⚠ {errors} errors</span>}
      </div>

      {details.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-slate-500 hover:text-slate-700 select-none">
            {details.length} failure{details.length !== 1 ? "s" : ""}
          </summary>
          <ul className="mt-1 space-y-0.5 pl-2 border-l-2 border-red-200">
            {details.map((d, i) => (
              <li key={i} className="text-red-700 font-mono truncate" title={d}>
                {d}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
