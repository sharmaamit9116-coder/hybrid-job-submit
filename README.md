# hybrid-job-submit
A small Python CLI that reads a YAML job manifest and **routes + submits** the job to: - **Slurm** for `job_type: training` - **Kubernetes** for `job_type: inference` - **Kubernetes (time-slicing hint)** for `job_type: interactive`
