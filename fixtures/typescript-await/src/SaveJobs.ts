type Job = { id: string };
declare function save(job: Job): Promise<void>;
declare function showSaved(): void;

// The caller awaits this before showing success or closing the editor.
export async function saveJobs(jobs: Job[]): Promise<void> {
  await jobs.forEach(async (job) => {
    await save(job);
  });
  showSaved();
}
