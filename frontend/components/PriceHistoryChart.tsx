"use client"
import { useEffect, useState } from "react"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"

interface PricePoint { price: number; recorded_at: string }

export default function PriceHistoryChart({ dealId, salePrice, originalPrice }: {
  dealId: number; salePrice: number; originalPrice: number
}) {
  const [data, setData] = useState<PricePoint[]>([])

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/deals/${dealId}/price-history`)
      .then(r => r.json()).then(setData).catch(() => {})
  }, [dealId])

  if (data.length < 2) return null  // 데이터 부족하면 숨김

  const formatted = data.map(d => ({
    date: new Date(d.recorded_at).toLocaleDateString("ko-KR", { month: "numeric", day: "numeric" }),
    price: Math.round(d.price / 1000) // 천원 단위
  }))

  return (
    <div className="mt-6 p-4 bg-gray-50 rounded-lg">
      <h3 className="text-[13px] font-semibold text-gray-700 mb-3">가격 추이</h3>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={formatted}>
          <XAxis dataKey="date" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${v}천`} />
          <Tooltip formatter={(v: number | undefined) => v != null ? `${v}천원` : ""} />
          {originalPrice > 0 && (
            <ReferenceLine
              y={Math.round(originalPrice / 1000)}
              stroke="#E31E24"
              strokeDasharray="3 3"
              label={{ value: "정가", fontSize: 9 }}
            />
          )}
          <Line type="monotone" dataKey="price" stroke="#2563EB" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
