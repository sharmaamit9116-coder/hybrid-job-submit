# hybrid-job-submit

A small Python CLI that reads a YAML job manifest and **routes + submits** the job to:
- **Slurm** for `job_type: training`
- **Kubernetes** for `job_type: inference`
- **Kubernetes (time-slicing hint)** for `job_type: interactive`

It enforces **per-team GPU quotas** (hard-coded, realistic defaults) and returns:
- **job_id**
- **backend**
- **expected_start_time** (best-effort)

> Minimal and interview-friendly: clear logic, meaningful errors, and runnable locally if you have `sbatch` and/or `kubectl` configured.

---

## Repo layout

```
hybrid-job-submit/
├── submit_job.py
├── hybrid_job_submit/
│   ├── __init__.py
│   ├── manifest.py
│   ├── quotas.py
│   ├── router.py
│   ├── errors.py
│   ├── utils.py
│   └── backends/
│       ├── __init__.py
│       ├── slurm_backend.py
│       └── k8s_backend.py
├── examples/
│   ├── job_manifest_training.yaml
│   ├── job_manifest_inference.yaml
│   └── job_manifest_interactive.yaml
├── k8s/
│   ├── templates/
│   │   ├── job.yaml.j2
│   │   └── pod.yaml.j2
│   └── prometheus/
│       └── low_gpu_utilization_alert.yaml
├── requirements.txt
└── .gitignore
```

---

## Quickstart

### 1) Create a venv + install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run with an example manifest

**Training → Slurm**
```bash
python submit_job.py --config examples/job_manifest_training.yaml
```

**Inference → Kubernetes**
```bash
python submit_job.py --config examples/job_manifest_inference.yaml
```

**Interactive → Kubernetes (time-slicing hint via annotations)**
```bash
python submit_job.py --config examples/job_manifest_interactive.yaml
```

---

## Dependencies / prerequisites

### Slurm submission
- Requires `sbatch` in PATH and access to a Slurm controller.
- Uses **sbatch** for submission and **squeue** (if available) to fetch a best-effort start time.

### Kubernetes submission
- Requires `kubectl` in PATH and a configured kubecontext.
- Creates a `Job` for inference and a `Pod` for interactive sessions.

> GPU time-slicing is cluster-dependent (NVIDIA device plugin time-slicing + policy).  
> This tool adds annotations/labels to express intent.

---

## Manifest schema

```yaml
team: vision-china
user: john.doe
job_type: training | inference | interactive
gpus: 32
duration_hours: 24
image: registry.lenovo.com/pytorch:2.4-cuda12.1
priority: normal | high
command: python train.py --model LLaMA-70B ...
```

Optional fields:
- `name` (string): job name override
- `namespace` (string): Kubernetes namespace (default: `team`)
- `workdir` (string): used by Slurm wrapper script (default: `/workspace`)
- `env` (map): environment variables

---

## Prometheus alert (optional)

See: `k8s/prometheus/low_gpu_utilization_alert.yaml`
