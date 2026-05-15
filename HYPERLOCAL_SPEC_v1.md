# Acre v1.0 Technical Specification

**Project Codename:** Acre

**Stack:** Python / FastAPI / arq / PostGIS / Ollama / ComfyUI

**Infrastructure:** Hetzner Dedicated (Cloud) + NucBox inference node

---

## 1. System Architecture

Acre is a distributed asynchronous platform designed to bridge cloud-based geospatial logic with localized physical fulfillment. The system is split into two primary environments connected via a secure **Tailscale/Cloudflare Tunnel**.

* **Cloud Layer (Hetzner):** Manages the web UI, PostGIS database, and the `arq` global task queue.
* **Intelligence Layer (NucBox):** Handles local text generation via **Ollama** and background generation via **ComfyUI/Z-Image Turbo**.
* **Fulfillment Layer (Print Node):** Local hardware agent polling for `READY_TO_PRINT` jobs.

---

## 2. Infrastructure & Tooling

* **Backend:** Python 3.12+ / FastAPI.
* **Task Orchestration:** `arq` (Redis-backed, native `asyncio`).
* **Geospatial DB:** PostgreSQL 16 + **PostGIS 3.4**.
* **Intelligence:** Ollama text generation + ComfyUI/Z-Image Turbo background generation on the NucBox.
* **PDF Engine:** `Typst` (Rust-based) for millisecond PDF compilation.

---

## 3. Core Service Modules

### A. The Geospatial Engine (PostGIS)

The engine identifies USPS Carrier Routes by intersecting a user-defined radius () with official USPS Tiger/Line shapefiles.

* **Query Logic:** Uses `ST_DWithin` on indexed geometry for sub-millisecond lookups.
* **Filter:** Excludes non-residential and P.O. Box routes to ensure 100% home delivery.

### B. The Intelligence Node (NucBox)

Triggered by an `arq` worker when a user requests "Generate Design."

1. **Context Scraper:** Pulls brand colors/logos from the user's URL.
2. **Ollama Inference:** NucBox Ollama generates high-conversion ad copy.
3. **Image Synthesis:** NucBox ComfyUI/Z-Image Turbo produces text-free background assets.
4. **Local Compute:** The canonical path avoids hosted image or LLM APIs for routine flyer generation.

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
* **Data:** All PII (Personally Identifiable Information) is encrypted at rest on Hetzner; default LLM and image inference remains on the private NucBox node.

---
