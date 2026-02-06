# Acre v1.0 Technical Specification

**Project Codename:** Acre

**Stack:** Python / FastAPI / arq / PostGIS / MLX

**Infrastructure:** Hetzner Dedicated (Cloud) + Apple M4 Max (Local Node)

---

## 1. System Architecture

Acre is a distributed asynchronous platform designed to bridge cloud-based geospatial logic with localized physical fulfillment. The system is split into two primary environments connected via a secure **Tailscale/Cloudflare Tunnel**.

* **Cloud Layer (Hetzner):** Manages the web UI, PostGIS database, and the `arq` global task queue.
* **Intelligence Layer (Local M4 Max):** Handles GPU-accelerated LLM inference for creative generation via **MLX**.
* **Fulfillment Layer (Print Node):** Local hardware agent polling for `READY_TO_PRINT` jobs.

---

## 2. Infrastructure & Tooling

* **Backend:** Python 3.12+ / FastAPI.
* **Task Orchestration:** `arq` (Redis-backed, native `asyncio`).
* **Geospatial DB:** PostgreSQL 16 + **PostGIS 3.4**.
* **Intelligence:** Llama 3.1 8B (via `mlx-lm`) + Stable Diffusion XL Turbo (local).
* **PDF Engine:** `Typst` (Rust-based) for millisecond PDF compilation.

---

## 3. Core Service Modules

### A. The Geospatial Engine (PostGIS)

The engine identifies USPS Carrier Routes by intersecting a user-defined radius () with official USPS Tiger/Line shapefiles.

* **Query Logic:** Uses `ST_DWithin` on indexed geometry for sub-millisecond lookups.
* **Filter:** Excludes non-residential and P.O. Box routes to ensure 100% home delivery.

### B. The Intelligence Node (M4 Max)

Triggered by an `arq` worker when a user requests "Generate Design."

1. **Context Scraper:** Pulls brand colors/logos from the user's URL.
2. **MLX Inference:** Local Llama 3.1 generates 3 variations of high-conversion ad copy.
3. **Image Synthesis:** Local SDXL-Turbo generates background assets.
4. **Zero-Cost:** By running compute on local Apple Silicon, Acre eliminates OpenAI/Anthropic API overhead.

### C. The Fulfillment Node (Local Agent)

A lightweight Python daemon running on the local "Node 0" machine.

* **Job Polling:** Monitors the `READY_TO_PRINT` status in the cloud DB.
* **Parallel Queueing:** Directs PDF pages across multiple connected hardware stacks using the system `lp` (Line Printer) queue.
* **Compliance Gen:** Programmatically renders **PS Form 3587** and carrier-route **Facing Slips** as PDF overlays.

---

## 4. Data Schema (Simplified)

| Table | Key Fields | Purpose |
| --- | --- | --- |
| `nodes` | `id`, `location_city`, `printer_count`, `status` | Tracks physical capacity. |
| `campaigns` | `id`, `user_id`, `radius`, `piece_count`, `status` | Main state machine for orders. |
| `routes` | `carrier_id`, `zip_code`, `res_count`, `geom` | PostGIS-indexed route data. |
| `creative_assets` | `id`, `campaign_id`, `image_path`, `copy_text` | Stores generated AI content. |

---

## 5. Scaling Logic: Parallel Throughput

Scaling is achieved by adding **Parallel Machine Units** to existing nodes rather than geographical expansion.

* **Metric:** Once a Node hits 5,000 pieces/week, a second hardware unit is added to the local `lp` queue.
* **Load Balancing:** The local agent round-robins print jobs across all verified "Active" printers in the stack to prevent hardware fatigue.

---

## 6. Connectivity & Security

* **Networking:** All local nodes connect to the Hetzner backend via **Tailscale Funnel**, ensuring no open ports.
* **Data:** All PII (Personally Identifiable Information) is encrypted at rest on Hetzner; LLM inference remains strictly local to the M4 Max.

---
