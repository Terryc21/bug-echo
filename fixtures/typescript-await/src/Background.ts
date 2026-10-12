type Job = { id: string };
declare function recordAnalytics(job: Job): Promise<void>;
declare function logFailure(error: unknown): void;

// Deliberately fire-and-forget telemetry; callers must not wait for it.
export function recordJobs(jobs: Job[]): void {
  jobs.forEach((job) => {
    void recordAnalytics(job).catch(logFailure);
  });
}
