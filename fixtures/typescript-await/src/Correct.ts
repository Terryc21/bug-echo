type Job = { id: string };
declare function save(job: Job): Promise<void>;
declare function showSaved(): void;

export async function saveJobs(jobs: Job[]): Promise<void> {
  await Promise.all(jobs.map((job) => save(job)));
  showSaved();
}
