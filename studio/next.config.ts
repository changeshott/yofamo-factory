import type { NextConfig } from "next";

const config: NextConfig = {
  // Studio hanya berjalan di laptop sendiri; tidak ada telemetry atau gambar remote.
  poweredByHeader: false,
  devIndicators: false,
};

export default config;
