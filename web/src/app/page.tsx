"use client";

import { useMemo, useState } from "react";
import { Fraunces, Space_Grotesk } from "next/font/google";

const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-grotesk" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });

const presets = {
  smoothie: {
    campaignId: 1,
    name: "Sunset Smoothie Co.",
    website: "sunsetsmoothie.co",
    address: "214 W 7th St",
    city: "Austin",
    state: "TX",
    postal: "78701",
    phone: "(512) 555-0142",
    hours: "Mon-Sat 8am-8pm, Sun 9am-6pm",
    serviceArea: "Downtown Austin",
    product: "Fresh smoothies and acai bowls",
    offer: "Buy one smoothie, get 50% off the second",
    tone: "bright, healthy, upbeat",
    cta: "Order Today",
    audience: "local families and gym-goers",
    constraints: "No people\nHigh contrast for readability\nInclude price/offer clearly",
    brandColors: "coral, mint green, sunny yellow, white",
    styleKeywords: "fresh, modern, clean, tropical",
  },
  realEstate: {
    campaignId: 2,
    name: "RapidKeys Home Buyers",
    website: "rapidkeyshomebuyers.com",
    address: "3800 N Lamar Blvd, Ste 200",
    city: "Austin",
    state: "TX",
    postal: "78756",
    phone: "(512) 555-0134",
    hours: "Mon-Fri 9am-6pm",
    serviceArea: "Austin Metro",
    product: "We buy houses for cash",
    offer: "Close in as little as 7 days. No repairs. No agent fees.",
    tone: "trustworthy, direct, professional",
    cta: "Get Cash Offer",
    audience: "homeowners needing to sell fast",
    constraints: "No people\nHighlight no repairs and no fees",
    brandColors: "navy, gold, white",
    styleKeywords: "professional, real-estate, clean, photographic",
  },
  hvac: {
    campaignId: 3,
    name: "Northside Plumbing & HVAC",
    website: "northsideplumbinghvac.com",
    address: "9150 Burnet Rd, Ste 110",
    city: "Austin",
    state: "TX",
    postal: "78758",
    phone: "(512) 555-0199",
    hours: "24/7 Emergency Service",
    serviceArea: "North & Central Austin",
    product: "24/7 emergency plumbing and AC repair",
    offer: "$79 service call. Free diagnostics with repair.",
    tone: "reliable, bold, reassuring",
    cta: "Call 24/7",
    audience: "local homeowners and small businesses",
    constraints: "No people\nInclude 'Licensed & insured'\nHighlight same-day service",
    brandColors: "blue, red, white",
    styleKeywords: "bold, trustworthy, industrial, clean",
  },
};

type PresetKey = keyof typeof presets;

type Result = {
  output_dir: string;
  variants: Array<{
    index: number;
    image_path: string;
    qc_passed: boolean;
    qc_text?: string | null;
  }>;
};

export default function Home() {
  const [preset, setPreset] = useState<PresetKey>("smoothie");
  const [form, setForm] = useState(presets.smoothie);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://localhost:18000";

  const updatePreset = (key: PresetKey) => {
    setPreset(key);
    setForm(presets[key]);
    setResult(null);
  };

  const resolveImageUrl = (path: string) => {
    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }
    if (path.startsWith("s3://")) {
      return "";
    }
    const cleaned = path.replace(/^\.?\//, "");
    return `${apiBase}/files/${cleaned}`;
  };

  const onSubmit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const payload = {
        campaign_id: form.campaignId,
        business_details: {
          name: form.name,
          website: form.website,
          address: form.address,
          city: form.city,
          state: form.state,
          postal_code: form.postal,
          phone: form.phone,
          hours: {
            display: form.hours,
            timezone: "America/Chicago",
          },
          service_area: form.serviceArea,
        },
        product: form.product,
        offer: form.offer,
        tone: form.tone,
        cta: form.cta,
        size: "6x9",
        audience: form.audience,
        constraints: form.constraints
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
        brand_colors: form.brandColors
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        style_keywords: form.styleKeywords
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        reference_images: [],
      };

      const response = await fetch(`${apiBase}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to generate flyer");
      }
      const data = (await response.json()) as Result;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`${grotesk.variable} ${fraunces.variable} min-h-screen bg-[radial-gradient(circle_at_top,_#ffe9c2,_#f9f7f2_45%,_#e6eef3_100%)] text-zinc-900`}
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-12 lg:flex-row">
        <aside className="flex w-full flex-col gap-6 rounded-3xl border border-black/10 bg-white/80 p-6 shadow-[0_20px_60px_-45px_rgba(15,23,42,0.6)] backdrop-blur lg:w-[420px]">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
              Hyperlocal Studio
            </p>
            <h1 className="text-3xl font-semibold font-[var(--font-fraunces)]">
              Flyer Generator
            </h1>
            <p className="text-sm text-zinc-600">
              Generate a 6x9 direct-mail flyer from a structured business
              profile and offers.
            </p>
          </div>

          <div className="flex gap-2 text-xs font-medium">
            {(["smoothie", "realEstate", "hvac"] as PresetKey[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => updatePreset(key)}
                className={`rounded-full border px-3 py-1 ${
                  preset === key
                    ? "border-black bg-black text-white"
                    : "border-black/10 bg-white text-zinc-600"
                }`}
              >
                {key === "smoothie"
                  ? "Smoothie"
                  : key === "realEstate"
                    ? "Real Estate"
                    : "Plumbing/HVAC"}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {[
              ["Business Name", "name"],
              ["Website", "website"],
              ["Address", "address"],
              ["City", "city"],
              ["State", "state"],
              ["Postal Code", "postal"],
              ["Phone", "phone"],
              ["Hours", "hours"],
              ["Service Area", "serviceArea"],
              ["Product", "product"],
              ["Offer", "offer"],
              ["Tone", "tone"],
              ["CTA", "cta"],
              ["Audience", "audience"],
            ].map(([label, key]) => (
              <label key={key} className="text-xs uppercase tracking-wide">
                <span className="text-zinc-500">{label}</span>
                <input
                  className="mt-1 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900"
                  value={(form as any)[key]}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, [key]: event.target.value }))
                  }
                />
              </label>
            ))}
          </div>

          <label className="text-xs uppercase tracking-wide">
            <span className="text-zinc-500">Constraints (one per line)</span>
            <textarea
              className="mt-1 h-24 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900"
              value={form.constraints}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, constraints: event.target.value }))
              }
            />
          </label>

          <label className="text-xs uppercase tracking-wide">
            <span className="text-zinc-500">Brand Colors (comma separated)</span>
            <input
              className="mt-1 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900"
              value={form.brandColors}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, brandColors: event.target.value }))
              }
            />
          </label>

          <label className="text-xs uppercase tracking-wide">
            <span className="text-zinc-500">Style Keywords</span>
            <input
              className="mt-1 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm text-zinc-900"
              value={form.styleKeywords}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  styleKeywords: event.target.value,
                }))
              }
            />
          </label>

          <button
            type="button"
            onClick={onSubmit}
            disabled={loading}
            className="mt-2 rounded-2xl bg-black px-4 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:-translate-y-0.5 disabled:opacity-70"
          >
            {loading ? "Generating..." : "Generate Flyer"}
          </button>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
            </div>
          )}
        </aside>

        <section className="flex-1 space-y-6">
          <div className="rounded-3xl border border-black/10 bg-white/80 p-6 shadow-[0_20px_60px_-45px_rgba(15,23,42,0.6)]">
            <h2 className="text-xl font-semibold font-[var(--font-fraunces)]">
              Output
            </h2>
            <p className="mt-2 text-sm text-zinc-600">
              Results appear here after generation. Images are served from the
              backend container.
            </p>
          </div>

          {result ? (
            <div className="grid gap-6 lg:grid-cols-2">
              {result.variants.map((variant) => {
                const imageUrl = resolveImageUrl(variant.image_path);
                return (
                  <div
                    key={variant.index}
                    className="rounded-3xl border border-black/10 bg-white/80 p-4 shadow-[0_20px_60px_-45px_rgba(15,23,42,0.6)]"
                  >
                    {imageUrl ? (
                      <img
                        src={imageUrl}
                        alt={`Variant ${variant.index}`}
                        className="w-full rounded-2xl border border-black/10"
                      />
                    ) : (
                      <div className="flex h-80 items-center justify-center rounded-2xl border border-dashed border-black/20 text-sm text-zinc-500">
                        Image unavailable
                      </div>
                    )}
                    <div className="mt-3 text-xs text-zinc-600">
                      QC: {variant.qc_passed ? "PASS" : "FAIL"}
                    </div>
                    {variant.qc_text && (
                      <pre className="mt-2 max-h-36 overflow-auto rounded-xl bg-black/90 p-3 text-[11px] text-emerald-100">
                        {variant.qc_text}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-3xl border border-black/10 bg-white/70 p-10 text-center text-sm text-zinc-500">
              Generate a flyer to preview results.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
