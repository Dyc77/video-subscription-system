/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    unoptimized: true,
  },
  // 必須將 allowedDevOrigins 放在頂層，而不是 experimental 區塊
  allowedDevOrigins: [
    'nchudyc.duckdns.org',
    'nchudyc.duckdns.org:3000',
    ...(process.env.NEXT_PUBLIC_API_URL
      ? [new URL(process.env.NEXT_PUBLIC_API_URL).host]
      : ['localhost:8000']
    ),
  ],
  // 減少開發模式下的錯誤輸出
  devIndicators: {
    buildActivity: false,
  },
  // 禁用 source maps 以減少錯誤訊息
  productionBrowserSourceMaps: false,
  // 使用 standalone 輸出模式，避免靜態導出問題
  output: 'standalone',
}


export default nextConfig
